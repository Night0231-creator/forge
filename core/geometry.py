"""OBJ mesh inspection and a reference-based size suggestion.

This tool does not know TaleSpire's intended height for every species; the
14-unit human reference is an empirical starting point, not a game standard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ObjStats:
    vertices: int
    faces: int
    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]

    @property
    def height(self) -> float:
        return self.max_xyz[1] - self.min_xyz[1]  # TaleWeaverCmd OBJ is Y-up


def inspect_obj(path: Path, max_faces: int | None = None):
    """Return bounds and optionally sampled face geometry for the viewer.

    When max_faces is provided, return (ObjStats, verts, faces). Otherwise
    return only ObjStats, and avoid storing all vertices in memory.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'OBJ nao encontrado: {path}')
    mins = [math.inf] * 3
    maxs = [-math.inf] * 3
    count, face_count = 0, 0
    vertices, faces = [], []
    with path.open('r', encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.split()
                if len(parts) < 4:
                    raise ValueError('Linha OBJ invalida: vertice incompleto.')
                coords = tuple(float(p) for p in parts[1:4])
                if not all(math.isfinite(c) for c in coords):
                    raise ValueError('OBJ com coordenadas invalidas.')
                for i, v in enumerate(coords):
                    mins[i] = min(mins[i], v)
                    maxs[i] = max(maxs[i], v)
                count += 1
                if max_faces is not None:
                    vertices.append(coords)
            elif line.startswith('f '):
                face_count += 1
                if max_faces is not None:
                    try:
                        ids = []
                        for p in line.split()[1:]:
                            number = int(p.split('/')[0])
                            index = number - 1 if number > 0 else count + number
                            if index < 0 or index >= count:
                                raise ValueError('indice fora dos limites')
                            ids.append(index)
                        if len(ids) >= 3:
                            faces.append(tuple(ids))
                    except (ValueError, IndexError):
                        continue
    if not count:
        raise ValueError('O modelo OBJ nao tem vertices.')
    stats = ObjStats(count, face_count, tuple(mins), tuple(maxs))
    if max_faces is None:
        return stats
    if len(faces) > max_faces:
        stride = math.ceil(len(faces) / max_faces)
        faces = faces[::stride][:max_faces]
    return stats, vertices, faces


def suggest_factor(obj_height: float, reference_height: float = 14.0) -> float:
    """Scale from current OBJ Y-height to a selected reference height."""
    if (not math.isfinite(obj_height) or not math.isfinite(reference_height)
            or obj_height <= 1e-6 or not 0.5 <= reference_height <= 40):
        raise ValueError('Altura invalida para ajuste automatico.')
    value = reference_height / obj_height
    if not 0.1 <= value <= 100:
        raise ValueError('Escala automatica fora do intervalo 0,1x a 100x. Ajuste o modelo no Blender.')
    return value
