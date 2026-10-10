"""Basecoat-inspired Meshy import defaults; not extracted from proprietary tsMod.

Only the reference's header/version/producer are discoverable by safe inspection.
No known metadata field encodes a trustworthy mesh scale or TaleSpire default
scale, so these are user-adjustable starting values, not a Basecoat clone.
"""
from __future__ import annotations

from pathlib import Path

BASECOAT_VISUAL_PRESET_NAME = 'Basecoat 1x1 (referencia visual)'
PRESET_HEIGHT = '1.75'
PRESET_ROTATION = '0'
PRESET_TRIANGLES = '100000'
PRESET_TEXTURE_SIZE = '2048'
PRESET_QUALITY = 'Alta'
PRESET_TARGET_HEIGHT = '1.75'
PRESET_MULTIPLIER = '1'
SUPPORTED_MESHY = {'.glb','.gltf','.fbx','.obj','.blend','.stl','.zip'}


def is_meshy_model(path: str) -> bool:
    """Apply when the user chooses an existing 3D source; not when editing a name."""
    p = Path(path.strip().strip('"')).expanduser()
    return p.suffix.lower() in SUPPORTED_MESHY and p.is_file()


def preset_values() -> dict[str, str | bool]:
    return {
        'height': PRESET_HEIGHT,
        'rotation': PRESET_ROTATION,
        'tris': PRESET_TRIANGLES,
        'resolution': PRESET_TEXTURE_SIZE,
        'quality': PRESET_QUALITY,
        'target_height': PRESET_TARGET_HEIGHT,
        'scale_factor': PRESET_MULTIPLIER,
        'auto_scale': True,
        'cmd_enabled': True,
        # Optional mod/plugin export is not needed for an official .tsMod.
        'plugin': False,
    }


def suggested_calibration_height(previous_target: float,
                                 observed_ratio: float) -> float:
    """User-entered in-game calibration, not inferred from .tsMod header.

    observed_ratio is reference apparent height divided by our mini height.
    Guards against accidentally creating a giant model.
    """
    import math
    if (not math.isfinite(previous_target) or not math.isfinite(observed_ratio)
            or previous_target <= 0 or observed_ratio <= 0):
        raise ValueError('Proporcao visual invalida.')
    new = previous_target * observed_ratio
    if not 0.5 <= new <= 5.0:
        raise ValueError('Altura fora do intervalo de calibracao 0,5–5,0.')
    return round(new, 3)
