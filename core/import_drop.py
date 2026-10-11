"""Safely identify one Meshy 3D model from a Windows/Tk drag-and-drop event."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .helpers import SUPPORTED, safe_slug


def parse_dropped_model(data: str, splitlist: Callable[[str], tuple | list]) -> Path:
    """Tk's splitlist handles quoted and {space-containing} file paths.

    Reject URLs, multiple files and unsupported types. Never move or execute
    the dropped file; only return a canonical path for the existing pipeline.
    """
    try:
        items = splitlist(data)
    except (ValueError, TypeError, RuntimeError) as exc:
        raise ValueError('Não foi possível ler o arquivo arrastado.') from exc
    if len(items) != 1:
        raise ValueError('Arraste apenas um modelo GLB ou ZIP por vez.')
    source = Path(str(items[0]).strip('"')).expanduser()
    if source.suffix.lower() not in SUPPORTED:
        raise ValueError('Selecione um modelo .GLB, .ZIP, .FBX, .OBJ ou .BLEND do Meshy.')
    if not source.is_file():
        raise ValueError('O arquivo arrastado não existe no computador.')
    return source.resolve()


def display_model_name(path: str | Path) -> str:
    return safe_slug(Path(path).stem)
