"""Read-only library index of completed Mini Forge projects.

Does not change generated models, manifests or .tsMod files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Miniature:
    folder: Path
    name: str
    tsmod: Path | None
    thumbnail: Path | None
    obj: Path | None
    updated_at: float


def scan_library(root: str | Path, max_items: int = 150) -> list[Miniature]:
    """Index only immediate project subfolders (avoid arbitrary recursive scans)."""
    root = Path(root).expanduser()
    if not root.is_dir():
        return []
    entries: list[Miniature] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for folder in children:
        if not folder.is_dir() or folder.is_symlink():
            continue
        tsmod = folder / f'{folder.name}.tsMod'
        if not tsmod.is_file():
            # Names sometimes differ from folder after the user renames them.
            tsmod = next(iter(sorted(folder.glob('*.tsMod'))), None)
        obj = folder / 'TaleWeaverCmd_Source' / f'{folder.name}.obj'
        if not obj.is_file():
            obj = next(iter(sorted((folder / 'TaleWeaverCmd_Source').glob('*.obj'))), None)
        thumb = next((p for p in [folder / 'Entrada_TaleWeaverCmd' / 'thumbnail.png',
                                  folder / 'TaleWeaverCmd_Source' / 'thumbnail.png',
                                  folder / 'thumbnail.png'] if p.is_file()), None)
        # Ignore arbitrary folders with no conversion data.
        if tsmod is None and obj is None and not (folder / 'conversao.json').is_file():
            continue
        try:
            updated = max(p.stat().st_mtime for p in [folder, tsmod, obj] if p is not None)
        except OSError:
            continue
        entries.append(Miniature(folder=folder, name=folder.name,
                                 tsmod=tsmod if tsmod and tsmod.is_file() else None,
                                 thumbnail=thumb, obj=obj, updated_at=updated))
    return sorted(entries, key=lambda item: item.updated_at, reverse=True)[:max_items]
