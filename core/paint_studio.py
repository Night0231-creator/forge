"""Non-destructive UV albedo painting for user-owned Astronyx miniatures.

This first studio milestone edits the existing UV atlas, not a 3D raycast mesh.
It NEVER rewrites a .tsMod; explicit apply updates local PNG sources with backups.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

from PIL import Image, ImageDraw, ImageColor

MAX_PIXELS = 4096 * 4096
HISTORY_LIMIT = 8
PALETTE = {
    'Aço': '#929FAC', 'Ouro': '#E4B54C', 'Cobre': '#A76B48',
    'Couro': '#70452F', 'Tecido': '#613E94', 'Pele': '#DEAB85',
    'Pedra': '#858898', 'Madeira': '#705139', 'Magia': '#8A64FF',
    'Verde': '#478E69', 'Branco': '#EFE8DF', 'Preto': '#292A38',
}


def find_albedo(project: str | Path) -> Path:
    root = Path(project).expanduser().resolve()
    for p in (root / 'TaleWeaverLite' / 'Albedo.png',
              root / 'TaleWeaverCmd_Source' / 'Albedo.png'):
        if p.is_file() and not p.is_symlink():
            return p
    raise FileNotFoundError('Albedo.png não encontrado. Converta a miniatura antes de pintar.')


def _project(root: str | Path) -> Path:
    root = Path(root).expanduser().resolve()
    if not (root / 'TaleWeaverCmd_Source').is_dir():
        raise ValueError('Selecione uma miniatura convertida pelo Mini Forge.')
    return root


class PaintSession:
    """Pillow-driven texture editing, with bounded snapshots and explicit saves."""
    def __init__(self, source: str | Path):
        self.source = Path(source).resolve()
        with Image.open(self.source) as raw:
            if raw.width < 1 or raw.height < 1 or raw.width * raw.height > MAX_PIXELS:
                raise ValueError('A textura deve ter até 4096×4096 pixels.')
            self.original = raw.convert('RGBA')
        self.image = self.original.copy()
        self.undo_stack: list[Image.Image] = []
        self.redo_stack: list[Image.Image] = []

    def checkpoint(self):
        self.undo_stack.append(self.image.copy())
        if len(self.undo_stack) > HISTORY_LIMIT:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        return True

    def pick(self, x: int, y: int) -> str:
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            raise ValueError('Selecione um pixel dentro da textura.')
        return '#%02X%02X%02X' % self.image.getpixel((x, y))[:3]

    def stroke(self, start: tuple[int, int], end: tuple[int, int],
               color: str, size: int = 18, opacity: float = 1.0,
               erase: bool = False):
        if not isinstance(size, int) or not 1 <= size <= 256:
            raise ValueError('Pincel deve ter tamanho 1–256.')
        if not math.isfinite(opacity) or not 0 < opacity <= 1:
            raise ValueError('Opacidade deve ficar entre 0 e 1.')
        rgb = ImageColor.getrgb(color)
        radius = max(1, size // 2)
        x0, y0 = start
        x1, y1 = end
        left = max(0, min(x0, x1) - radius - 2)
        top = max(0, min(y0, y1) - radius - 2)
        right = min(self.image.width, max(x0, x1) + radius + 3)
        bottom = min(self.image.height, max(y0, y1) + radius + 3)
        if right <= left or bottom <= top:
            return
        box = (left, top, right, bottom)
        mask = Image.new('L', (right-left, bottom-top), 0)
        draw = ImageDraw.Draw(mask)
        a = (x0-left, y0-top)
        b = (x1-left, y1-top)
        draw.line((a, b), fill=255, width=size)
        for cx, cy in (a, b):
            draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=255)
        if opacity < 1:
            mask = mask.point(lambda alpha: round(alpha*opacity))
        if erase:
            fill = self.original.crop(box)
        else:
            fill = Image.new('RGBA', mask.size, rgb + (255,))
        # Preserve the current surface alpha and blend only under the mask.
        base = self.image.crop(box)
        composed = Image.composite(fill, base, mask)
        self.image.paste(composed, box)

    def bucket(self, x: int, y: int, color: str, tolerance: int = 12):
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            raise ValueError('Clique dentro da textura.')
        if not 0 <= tolerance <= 100:
            raise ValueError('Tolerância inválida.')
        rgba = ImageColor.getrgb(color) + (255,)
        ImageDraw.floodfill(self.image, (x, y), rgba, thresh=tolerance)

    def save_draft(self, project: str | Path) -> Path:
        root = _project(project)
        dest_dir = root / 'Pintura'
        if dest_dir.is_symlink():
            raise ValueError('Diretório de pintura não pode ser um link simbólico.')
        dest_dir.mkdir(exist_ok=True)
        out = dest_dir / 'Albedo_editado.png'
        if out.is_symlink():
            raise ValueError('Arquivo de pintura não pode ser um link simbólico.')
        _write_png(self.image, out)
        manifest = {
            'schema': 'astronyx-paint-studio-v1',
            'source_file': self.source.name,
            'draft': out.name,
            'size': list(self.image.size),
            'uv_atlas_editor': True,
            'paint_on_3d_surface': False,
            'tsmod_exported': False,
        }
        (dest_dir / 'pintura.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        return out


def _write_png(image: Image.Image, target: Path):
    """Atomic write: a failure never leaves a truncated target PNG."""
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.astronyx-', suffix='.png',
                                         dir=target.parent, delete=False) as fp:
            tmp = Path(fp.name)
        image.save(tmp, format='PNG')
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def apply_paint_to_export(project: str | Path, draft: str | Path) -> list[Path]:
    """Apply to active conversion input/staging with backups; leave .tsMod alone.

    Retained drafts can be re-applied after running a new Blender conversion.
    The .tsMod itself is regenerated using the existing official TaleWeaverCmd.
    """
    root = _project(project)
    draft = Path(draft).resolve()
    safe_drafts = (root / 'Pintura').resolve()
    if not draft.is_file() or not draft.is_relative_to(safe_drafts):
        raise ValueError('Selecione um rascunho salvo na pasta Pintura da miniatura.')
    with Image.open(draft) as raw:
        if raw.width * raw.height > MAX_PIXELS:
            raise ValueError('Rascunho acima do limite de textura.')
        edited = raw.convert('RGBA')
    targets = [
        root / 'TaleWeaverLite' / 'Albedo.png',
        root / 'TaleWeaverCmd_Source' / 'Albedo.png',
        root / 'Entrada_TaleWeaverCmd' / 'albedo.png',
    ]
    targets = [p for p in targets if p.is_file()]
    if not targets:
        raise FileNotFoundError('Não há texturas de exportação para atualizar.')
    for p in targets:
        if p.is_symlink() or p.parent.is_symlink() or not p.resolve().is_relative_to(root):
            raise ValueError('Link simbólico inesperado na textura; ação cancelada.')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    # All backup copies are made before ANY conversion-input PNG is modified.
    for p in targets:
        backup = p.with_name(p.name + '.' + timestamp + '.bak')
        shutil.copy2(p, backup)
    for p in targets:
        _write_png(edited, p)
    return targets
