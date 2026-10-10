"""Conservative geometry budgeting for TaleWeaverCmd OBJ exports.

The Unity importer can create a new vertex at every UV seam or hard normal,
even if Blender reports only one vertex at that position. OBJ face-corner
(v / vt / vn / material) combinations provide a better preflight estimate.
The final Unity count may still differ, so the TaleWeaverCmd result is authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

MAX_TALEWEAVER_VERTICES = 60000
SAFE_SPLIT_VERTEX_TARGET = 48000


@dataclass(frozen=True)
class ObjVertexBudget:
    positions: int
    split_vertices: int
    faces: int
    face_corners: int

    @property
    def exceeds_limit(self) -> bool:
        return self.split_vertices > MAX_TALEWEAVER_VERTICES


def inspect_obj_vertex_budget(path: Path) -> ObjVertexBudget:
    """Read OBJ once. Count unique position/UV/normal/material face-corners.

    Does not parse coordinates or modify the source file. Missing faces produce
    zero split vertices; geometry validation remains the exporter's responsibility.
    """
    unique = set()
    positions = 0
    faces = 0
    corners = 0
    material = ""
    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            if line.startswith("v "):
                positions += 1
            elif line.startswith("usemtl "):
                material = line[7:].strip()
            elif line.startswith("f "):
                refs = line.split()[1:]
                if len(refs) < 3:
                    raise ValueError("Arquivo OBJ contém face com menos de três vértices.")
                faces += 1
                corners += len(refs)
                for ref in refs:
                    # The exported OBJ references are already canonicalized
                    # by Blender. Include UV/normal and material distinctions.
                    # Defensive: empty references are invalid.
                    if not ref.split("/")[0]:
                        raise ValueError("Arquivo OBJ contém índices de face inválidos.")
                    unique.add((material, ref))
    return ObjVertexBudget(positions, len(unique), faces, corners)


def next_triangle_budget(current: int, reported: int, *, target: int = SAFE_SPLIT_VERTEX_TARGET) -> int:
    """Lower face budget proportionally to observed OBJ/Unity split count.

    Supports retrying an original Meshy GLB conversion after a real Unity
    exception. Never increases triangles and never loops at identical budgets.
    """
    if current <= 500 or reported <= 0 or target <= 0:
        raise ValueError("Orçamento de vértices inválido.")
    if reported <= target:
        return current
    ratio = min(0.8, target / reported * 0.93)
    result = max(500, int(current * ratio))
    if result >= current:
        result = current - 1
    return result


def unity_vertex_exception(log: str) -> tuple[int, int] | None:
    """Extract authoritative Unity vertex overflow even amid shader warnings."""
    match = re.search(
        r"(?:creature|mesh)\s+has\s+([\d,._\s]+)\s+vertices\s+which\s+exceeds\s+"
        r"(?:the\s+)?max(?:imum)?\s+allowed\s+count\s+of\s+([\d,._\s]+)",
        log, re.IGNORECASE)
    if not match:
        return None
    def number(value: str) -> int:
        return int(re.sub(r"[^\d]", "", value))
    return number(match.group(1)), number(match.group(2))


def vertex_error_message(count: int, limit: int = MAX_TALEWEAVER_VERTICES) -> str:
    return (
        f"Modelo excedeu o limite de vértices do TaleWeaverCmd: "
        f"{count:,} de {limit:,} permitidos. "
        "A contagem do Unity pode aumentar por costuras UV e normais. "
        "Converta novamente o GLB original do Meshy com menos triângulos "
        "(por exemplo 45.000) ou use a redução automática na versão atualizada. "
        "Repetir apenas Gerar .tsMod não otimiza a malha."
    )
