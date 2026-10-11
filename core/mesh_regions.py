"""Connected regions split at sharp geometry edges, independent of atlas colors.

Welds coincident OBJ positions to recognize UV seams. Non-manifold edges do
not join regions. This is geometric segmentation, not semantic/AI selection.
"""
from __future__ import annotations

from collections import deque
import math
import numpy as np
from PIL import Image, ImageDraw


class MeshRegions:
    def __init__(self, mesh):
        self.mesh = mesh
        points = np.asarray(mesh.points, dtype=np.float64)
        faces = np.asarray(mesh.triangles, dtype=np.int32)
        if (points.ndim != 2 or points.shape[1] != 3 or not len(points)
                or faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
                or not np.isfinite(points).all()
                or faces.min() < 0 or faces.max() >= len(points)):
            raise ValueError('Malha inválida para selecionar regiões.')
        extent = max(float(np.ptp(points, axis=0).max()), 1e-6)
        # Relative tolerance merges exact/near duplicate OBJ positions only.
        _, welded = np.unique(np.rint((points-points.min(axis=0)) / (extent*1e-7)),
                              axis=0, return_inverse=True)
        corners = welded[faces]
        edges = np.stack((corners, np.roll(corners, -1, axis=1)), axis=-1)
        edges = np.sort(edges.reshape(-1, 2), axis=1)
        order = np.lexsort((edges[:, 1], edges[:, 0]))
        sorted_edges = edges[order]
        changes = np.r_[True, np.any(sorted_edges[1:] != sorted_edges[:-1], axis=1)]
        starts = np.flatnonzero(changes)
        counts = np.diff(np.r_[starts, len(order)])
        paired = starts[counts == 2]
        paired = paired[sorted_edges[paired, 0] != sorted_edges[paired, 1]]
        first, second = order[paired], order[paired+1]
        self.neighbors = np.full((len(faces), 3), -1, dtype=np.int32)
        self.neighbors[first//3, first%3] = second//3
        self.neighbors[second//3, second%3] = first//3
        tri = points[faces]
        normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        self.valid = lengths > extent*extent*1e-12
        self.normals = normals / np.maximum(lengths[:, None], 1e-30)
        self._last_key = None
        self._last_region = None

    def region(self, seed: int, angle: float = 35) -> np.ndarray:
        if (not isinstance(seed, (int, np.integer)) or not 0 <= seed < len(self.neighbors)
                or not math.isfinite(angle) or not 0 <= angle <= 180):
            raise ValueError('Face ou ângulo de região inválido.')
        key = (int(seed), float(angle))
        if key == self._last_key:
            return self._last_region.copy()
        visited = np.zeros(len(self.neighbors), dtype=bool)
        visited[seed] = True
        queue = deque([seed])
        cosine = math.cos(math.radians(angle)) - 1e-7
        while queue:
            current = queue.popleft()
            for neighbor in self.neighbors[current]:
                if (neighbor < 0 or visited[neighbor] or not self.valid[neighbor]
                        or not self.valid[current]):
                    continue
                if float(np.dot(self.normals[current], self.normals[neighbor])) >= cosine:
                    visited[neighbor] = True
                    queue.append(int(neighbor))
        result = np.flatnonzero(visited)
        self._last_key, self._last_region = key, result
        return result.copy()

    def mask(self, faces, size: tuple[int, int]) -> Image.Image:
        width, height = size
        if min(size) < 1 or width*height > 4096*4096:
            raise ValueError('Resolução inválida para regiões.')
        result = Image.new('L', size)
        draw = ImageDraw.Draw(result)
        for uv in self.mesh.texcoords[np.asarray(faces, dtype=np.int32)]:
            if not np.isfinite(uv).all():
                continue
            draw.polygon([(float(u)*(width-1), (1-float(v))*(height-1))
                          for u, v in uv], fill=255)
        return result
