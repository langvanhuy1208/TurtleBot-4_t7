"""Deterministic tests of map conversion, segmentation and command validation."""
import math
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from semantic_map import OccupancyMap, RegionCatalog
from segment_map import segment


@pytest.fixture
def catalog():
    return RegionCatalog(ROOT / 'maps/bai7/regions.yaml')


@pytest.mark.parametrize('text, expected', [
    ('Đi đến khu vực A.', ['A']),
    ('Đi đến khu A', ['A']),
    ('Đi đến khu B', ['B']),
    ('Đi đến khu C', ['C']),
    ('Đi đến khu bê', ['B']),
    ('Đi đến khu xê', ['C']),
    ('Di chuyển từ khu A đến khu B', ['A', 'B']),
    ('Đi từ khu A qua khu C rồi đến khu B', ['A', 'C', 'B']),
    ('Di chuyển từ khu vực A đến khu vực B.', ['A', 'B']),
    ('Đi đến phòng thí nghiệm.', ['B']),
    ('Đi từ phòng A qua hành lang rồi đến phòng B', ['A', 'C', 'B']),
    ('DI CHUYEN DEN HANH LANG', ['C']),
    ('Vui lòng đi đến khu vực bê', ['B']),
    ('Đi tới khu vực xê', ['C']),
    ('Đi đến Hành Lan.', ['C']),
    ('Dừng lại', []), ('Hủy điều hướng!', []),
])
def test_supported_commands(catalog, text, expected):
    assert catalog.parse(text) == expected


@pytest.mark.parametrize('text', [
    '', 'Đi đến khu vực Z', 'Đi từ khu vực Z đến khu vực B',
    'Đi và phụ A', 'Đi đến khu Z', 'Đi từ khu A qua khu Z đến khu B',
    'Đi từ phòng A qua phòng Z rồi đến phòng B',
    'Đừng đi đến khu vực A', 'Không đi đến phòng B',
    'Phòng A', 'Tôi đang xem phòng A và phòng B',
    'Đi đến khu vực AB', 'Đi đến phòng thí nghiệm Z',
    'Đi đến A rồi đến', 'Đi đến A và B',
])
def test_reject_entire_unknown_or_ambiguous_command(catalog, text):
    with pytest.raises(ValueError):
        catalog.parse(text)


def test_current_map_goals(catalog):
    assert len(catalog.regions) >= 3
    for region in catalog.regions.values():
        u, v = catalog.map.world_to_pixel(region['goal']['x'], region['goal']['y'])
        assert catalog.map.free[v, u]
        assert catalog.map.clearance[v, u] >= 0.35
    # All goals belong to the same robot-sized connected component.
    safe = (catalog.map.clearance >= 0.25).astype(np.uint8)
    _, connected = cv2.connectedComponents(safe, connectivity=4)
    components = set()
    for region in catalog.regions.values():
        u, v = catalog.map.world_to_pixel(region['goal']['x'], region['goal']['y'])
        components.add(connected[v, u])
    assert len(components) == 1 and 0 not in components


@pytest.mark.parametrize('yaw', [0, math.pi/2, -0.7])
def test_rotated_origin_roundtrip(tmp_path, yaw):
    cv2.imwrite(str(tmp_path/'image.pgm'), np.full((20, 30), 254, np.uint8))
    meta = dict(image='image.pgm', mode='trinary', resolution=0.05,
                origin=[-2, 3, yaw], negate=0, free_thresh=0.25, occupied_thresh=0.65)
    (tmp_path/'map.yaml').write_text(yaml.safe_dump(meta))
    m = OccupancyMap(tmp_path/'map.yaml')
    for pixel in [(0, 0), (29, 19), (11, 7)]:
        assert m.world_to_pixel(*m.pixel_to_world(*pixel)) == pixel
    assert m.clearance[0, 0] == pytest.approx(0.05)


def test_segmentation_respects_obstacles_and_goals(tmp_path):
    data = segment(ROOT/'maps/bai7/map.yaml', ROOT/'config/regions_seed.yaml', tmp_path)
    m = OccupancyMap(ROOT/'maps/bai7/map.yaml')
    labels = cv2.imread(str(tmp_path/'labels.png'), cv2.IMREAD_UNCHANGED)
    assert not labels[~m.free].any()
    assert set(np.unique(labels)) == {0, 1, 2, 3}
    assert len(RegionCatalog(tmp_path/'regions.yaml').regions) == 3
    assert data['method'] == 'manual-seeds-geodesic-voronoi'


def test_reject_modified_map(tmp_path):
    data = yaml.safe_load((ROOT/'maps/bai7/regions.yaml').read_text())
    data['map'] = str(ROOT/'maps/bai7/map.yaml')
    data['map_sha256'] = 'bad'
    (tmp_path/'regions.yaml').write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match='Map changed'):
        RegionCatalog(tmp_path/'regions.yaml')


def test_invalid_goal_fails_closed(tmp_path):
    data = yaml.safe_load((ROOT/'maps/bai7/regions.yaml').read_text())
    data['map'] = str(ROOT/'maps/bai7/map.yaml')
    data['labels'] = str(ROOT/'maps/bai7/labels.png')
    data['regions'][0]['goal']['x'] = 10000
    (tmp_path/'regions.yaml').write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match='outside map'):
        RegionCatalog(tmp_path/'regions.yaml')
