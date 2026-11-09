#!/usr/bin/env python3
"""Rasterize this repository's static, axis-aligned Gazebo maze collision boxes.

This is a geometry reference map, not a SLAM measurement. Reject unsupported
shapes/rotations rather than silently generating a misleading map.
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import yaml


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--world', default='worlds/maze_fast.sdf')
    p.add_argument('--output', default='maps/bai7')
    a = p.parse_args()
    resolution, low, high = 0.05, -10.5, 10.5
    width = int(round((high-low)/resolution))
    image = np.full((width, width), 205, dtype=np.uint8)
    coords = low + (np.arange(width)+0.5)*resolution
    xx, yy = np.meshgrid(coords, coords[::-1])
    image[(np.abs(xx)<10) & (np.abs(yy)<10)] = 254
    for model in ET.parse(a.world).getroot().findall('./world/model'):
        if model.findtext('static') not in ('true', '1'):
            raise ValueError(f'Expected static model: {model.get("name")}')
        mp = [float(v) for v in model.findtext('pose', '0 0 0 0 0 0').split()]
        if any(abs(v)>1e-6 for v in mp[3:]):
            raise ValueError('Rotated models are unsupported')
        for link in model.findall('link'):
            lp = [float(v) for v in link.findtext('pose', '0 0 0 0 0 0').split()]
            if any(abs(v)>1e-6 for v in lp[3:]):
                raise ValueError('Rotated links are unsupported')
            for collision in link.findall('collision'):
                if collision.find('geometry/plane') is not None:
                    continue
                box = collision.findtext('geometry/box/size')
                cp = [float(v) for v in collision.findtext('pose', '0 0 0 0 0 0').split()]
                if box is None or any(abs(v)>1e-6 for v in cp[3:]):
                    raise ValueError('Only axis-aligned box collisions supported')
                sx, sy, _sz = [float(v) for v in box.split()]
                x, y = mp[0]+lp[0]+cp[0], mp[1]+lp[1]+cp[1]
                # Include every cell intersecting a wall, including thin borders.
                image[(np.abs(xx-x) <= sx/2+resolution/2) &
                      (np.abs(yy-y) <= sy/2+resolution/2)] = 0
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out/'map.pgm'), image)
    (out/'map.yaml').write_text(yaml.safe_dump(dict(
        image='map.pgm', mode='trinary', resolution=resolution,
        origin=[low, low, 0], negate=0, occupied_thresh=0.65, free_thresh=0.196), sort_keys=False))
    (out/'provenance.txt').write_text(
        'Geometry reference occupancy map rasterized from worlds/maze_fast.sdf.\n'
        'Frame map is aligned with Gazebo world; this is NOT a SLAM result.\n'
        'Original recorded SLAM map remains untouched in maps/phase2/.\n')
    print(out/'map.yaml')


if __name__ == '__main__':
    main()
