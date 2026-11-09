#!/usr/bin/env python3
"""Map geometry, validated semantic destinations and strict Vietnamese grammar."""
from pathlib import Path
import hashlib
import math
import re
import unicodedata

import cv2
import numpy as np
import yaml


def normalize(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9\s]', ' ', text).split())


class OccupancyMap:
    def __init__(self, filename):
        self.path = Path(filename).resolve()
        self.meta = yaml.safe_load(self.path.read_text())
        if self.meta.get('mode', 'trinary') != 'trinary':
            raise ValueError('Only trinary OccupancyGrid maps are supported')
        self.image_path = self.path.parent / self.meta['image']
        self.image = cv2.imread(str(self.image_path), cv2.IMREAD_GRAYSCALE)
        if self.image is None:
            raise ValueError(f'Cannot read map: {self.image_path}')
        self.height, self.width = self.image.shape
        self.resolution = float(self.meta['resolution'])
        self.origin = [float(v) for v in self.meta['origin']]
        if self.resolution <= 0 or len(self.origin) != 3 or not all(
                math.isfinite(v) for v in [self.resolution, *self.origin]):
            raise ValueError('Invalid resolution/origin')
        occupancy = self.image.astype(float) / 255
        if not self.meta.get('negate', 0):
            occupancy = 1 - occupancy
        self.free = occupancy < float(self.meta['free_thresh'])
        # Padding treats the image boundary as an obstacle too.
        padded = np.pad(self.free.astype(np.uint8), 1)
        self.clearance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1] * self.resolution

    def pixel_to_world(self, u, v):
        x = (u + 0.5) * self.resolution
        y = (self.height - v - 0.5) * self.resolution
        ox, oy, yaw = self.origin
        return (ox + math.cos(yaw)*x - math.sin(yaw)*y,
                oy + math.sin(yaw)*x + math.cos(yaw)*y)

    def world_to_pixel(self, x, y):
        ox, oy, yaw = self.origin
        dx, dy = x-ox, y-oy
        px = (math.cos(yaw)*dx + math.sin(yaw)*dy) / self.resolution
        py = (-math.sin(yaw)*dx + math.cos(yaw)*dy) / self.resolution
        return math.floor(px), self.height - 1 - math.floor(py)

    def fingerprint(self):
        payload = self.image_path.read_bytes() + yaml.safe_dump(self.meta, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()


class RegionCatalog:
    def __init__(self, filename):
        self.path = Path(filename).resolve()
        self.data = yaml.safe_load(self.path.read_text())
        self.map = OccupancyMap(self.path.parent / self.data['map'])
        if self.map.fingerprint() != self.data['map_sha256']:
            raise ValueError('Map changed; regenerate segmentation before navigation')
        self.regions = {}
        self.aliases = {}
        labels = cv2.imread(str(self.path.parent / self.data['labels']), cv2.IMREAD_UNCHANGED)
        if labels is None or labels.shape != self.map.image.shape:
            raise ValueError('Invalid region label image')
        minimum = float(self.data['minimum_clearance_m'])
        if not math.isfinite(minimum) or minimum <= 0:
            raise ValueError('minimum_clearance_m must be positive')
        for region in self.data['regions']:
            rid = region['id']
            if rid in self.regions:
                raise ValueError(f'Duplicate region ID: {rid}')
            x, y, yaw = [float(region['goal'][key]) for key in ('x', 'y', 'yaw')]
            if not all(math.isfinite(v) for v in (x, y, yaw)):
                raise ValueError(f'Invalid goal: {rid}')
            u, v = self.map.world_to_pixel(x, y)
            if not (0 <= u < self.map.width and 0 <= v < self.map.height):
                raise ValueError(f'Goal outside map: {rid}')
            if (not self.map.free[v, u] or self.map.clearance[v, u] < minimum
                    or labels[v, u] != region['label']):
                raise ValueError(f'Goal blocked, too near wall or outside region: {rid}')
            self.regions[rid] = region
            for alias in [rid, region['name'], *region.get('aliases', [])]:
                key = normalize(alias)
                if not key or (key in self.aliases and self.aliases[key] != rid):
                    raise ValueError(f'Empty/ambiguous alias: {alias}')
                self.aliases[key] = rid
        if not self.regions:
            raise ValueError('Empty catalog')

    def resolve(self, name):
        key = normalize(name)
        if key not in self.aliases:
            raise ValueError(f'Khu vực không tồn tại: {name}')
        return self.aliases[key]

    def parse(self, text):
        """Return an ordered itinerary, or [] for cancellation. Reject entire bad route."""
        command = normalize(text)
        if command in ('dung', 'dung lai', 'huy', 'huy dieu huong'):
            return []
        command = re.sub(r'^(?:robot |hay |vui long )+', '', command)
        match = re.fullmatch(r'(?:di chuyen|dieu huong|di)(?: tu)? (.+)', command)
        if not match:
            raise ValueError('Lệnh không hợp lệ. Ví dụ: Đi đến khu vực A')
        route = match.group(1)
        route = re.sub(r'^(?:den|toi) ', '', route)
        # Every segment is resolved; unknown intermediate regions cannot be skipped.
        parts = re.split(r' (?:roi den|roi toi|sau do den|den|toi|qua) ', route)
        if not 1 <= len(parts) <= 10:
            raise ValueError('Lộ trình cần từ 1 đến 10 điểm')
        return [self.resolve(part) for part in parts]
