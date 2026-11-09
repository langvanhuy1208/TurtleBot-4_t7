#!/usr/bin/env python3
"""Seeded geodesic segmentation on known free space (no wall crossing)."""
import argparse
from collections import deque
from pathlib import Path
import math

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont
from semantic_map import OccupancyMap, RegionCatalog


def segment(map_file, seeds_file, output):
    m = OccupancyMap(map_file)
    config = yaml.safe_load(Path(seeds_file).read_text())
    regions = config['regions']
    minimum = float(config['minimum_clearance_m'])
    if not 3 <= len(regions) <= 65534 or not math.isfinite(minimum) or minimum <= 0:
        raise ValueError('Need 3..65534 regions and positive clearance')
    labels = np.zeros(m.image.shape, dtype=np.uint16)
    queue = deque()
    for index, region in enumerate(regions, 1):
        u, v = m.world_to_pixel(*region['seed'])
        if not (0 <= u < m.width and 0 <= v < m.height) or not m.free[v, u]:
            raise ValueError(f'Seed {region["id"]} must lie in known free space')
        if labels[v, u]:
            raise ValueError('Seeds must occupy distinct pixels')
        labels[v, u] = index
        queue.append((u, v))
    # Multisource BFS = Voronoi in geodesic distance over four-connected free cells.
    while queue:
        u, v = queue.popleft()
        for x, y in ((u-1, v), (u+1, v), (u, v-1), (u, v+1)):
            if 0 <= x < m.width and 0 <= y < m.height and m.free[y, x] and labels[y, x] == 0:
                labels[y, x] = labels[v, u]
                queue.append((x, y))
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    palette = [(70, 150, 240), (245, 170, 65), (80, 195, 135), (180, 100, 220)]
    rgb = cv2.cvtColor(m.image, cv2.COLOR_GRAY2RGB)
    result = []
    for index, region in enumerate(regions, 1):
        mask = labels == index
        safe_v, safe_u = np.where(mask & (m.clearance >= minimum))
        if not len(safe_u):
            raise ValueError(f'No safe destination in region {region["id"]}')
        # Destination closest to the desired seed, constrained by actual clearance.
        seed_u, seed_v = m.world_to_pixel(*region['seed'])
        best = np.argmin((safe_u-seed_u)**2 + (safe_v-seed_v)**2)
        u, v = int(safe_u[best]), int(safe_v[best])
        x, y = m.pixel_to_world(u, v)
        result.append(dict(id=region['id'], name=region['name'], label=index,
                           aliases=region.get('aliases', []), seed=region['seed'],
                           area_m2=round(float(mask.sum())*m.resolution**2, 3),
                           goal=dict(x=round(x, 6), y=round(y, 6), yaw=0.0),
                           clearance_m=round(float(m.clearance[v, u]), 3)))
        rgb[mask] = (0.3 * rgb[mask] + 0.7 * np.array(palette[(index-1) % len(palette)])).astype(np.uint8)
    import os
    data = dict(version=1, frame_id='map', method='manual-seeds-geodesic-voronoi',
                map=os.path.relpath(m.path, out), map_sha256=m.fingerprint(),
                labels='labels.png', minimum_clearance_m=minimum,
                unassigned_free_cells=int(np.sum(m.free & (labels == 0))), regions=result)
    cv2.imwrite(str(out / 'labels.png'), labels)
    (out / 'regions.yaml').write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    picture = Image.fromarray(rgb).resize((m.width*2, m.height*2))
    canvas = Image.new('RGB', (max(picture.width, 820), picture.height+160), 'white')
    canvas.paste(picture, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
    for index, region in enumerate(result):
        u, v = m.world_to_pixel(region['goal']['x'], region['goal']['y'])
        draw.ellipse((u*2-8, v*2-8, u*2+8, v*2+8), fill='white', outline='black', width=2)
        draw.text((u*2+10, v*2-20), region['id'], fill='black', font=font)
        draw.text((15, picture.height+10+index*32),
                  f'{region["id"]}: {region["name"]} | đích ({region["goal"]["x"]:.2f}, '
                  f'{region["goal"]["y"]:.2f}) m', fill=palette[index % len(palette)], font=font)
    draw.text((15, picture.height+112), 'Vùng chức năng từ hạt giống thủ công; xám = vật cản/chưa biết/không gán.', fill='black', font=font)
    canvas.save(out / 'segmented_map.png')
    RegionCatalog(out / 'regions.yaml')
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map', required=True)
    p.add_argument('--seeds', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    print(yaml.safe_dump(segment(args.map, args.seeds, args.output), allow_unicode=True, sort_keys=False))
