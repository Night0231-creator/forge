"""V2.4: non-destructive Albedo layers and TaleWeaverLite MAES material presets.

No claim of GPU/PBR preview. The RGBA MAES *data* channels are stored as
(R=metallic,G=AO,B=emissive,A=smoothness), not composited as visual alpha.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageOps
import numpy as np

from .paint_studio import PaintSession, MAX_PIXELS, _project, _write_png
from .brushes import coverage, segment_distance, stamp_mask

PRESETS = {
    'Aço escovado': (210, 235, 0, 175),
    'Ouro polido': (240, 240, 0, 225),
    'Bronze': (210, 225, 0, 155),
    'Couro': (0, 240, 0, 74),
    'Tecido fosco': (0, 230, 0, 35),
    'Pele': (0, 240, 0, 63),
    'Pedra': (0, 222, 0, 30),
    'Cristal mágico': (40, 235, 180, 215),
}
MAX_LAYERS = 8
MAX_HISTORY = 4


@dataclass
class PaintLayer:
    name: str
    pixels: Image.Image
    visible: bool = True
    opacity: int = 100


def _source_digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def _flood_mask(image: Image.Image, xy: tuple[int, int], tolerance: int) -> Image.Image:
    """Find only the connected region with colors similar to the seed pixel."""
    x, y = xy
    if not (0 <= x < image.width and 0 <= y < image.height):
        raise ValueError('Clique dentro da textura.')
    if not isinstance(tolerance, int) or not 0 <= tolerance <= 60:
        raise ValueError('Tolerância deve ficar entre 0 e 60.')
    before = image.convert('RGB')
    after = before.copy()
    seed = before.getpixel((x, y))
    sentinel = tuple((value + 128) % 256 for value in seed)
    ImageDraw.floodfill(after, (x, y), sentinel, thresh=tolerance)
    differences = ImageChops.difference(before, after).convert('L')
    return differences.point(lambda v: 255 if v else 0)


def find_maes(root: Path) -> Path | None:
    for p in (root / 'TaleWeaverLite' / 'MAES.png',
              root / 'TaleWeaverCmd_Source' / 'MAES.png'):
        if p.is_file() and not p.is_symlink():
            return p
    return None


class LayeredPaintSession(PaintSession):
    """PaintSession-compatible API used by both the UV and 3D viewers."""
    def __init__(self, source: str | Path, project: str | Path):
        super().__init__(source)
        self.project = _project(project)
        self.base = self.original.copy()
        self.layer_limit = min(MAX_LAYERS, max(2, (96*1024*1024) //
                                                  (self.image.width*self.image.height*4)))
        self.layers = [PaintLayer('Camada 1', Image.new('RGBA', self.image.size))]
        self.active_layer = 0
        self.selection: Image.Image | None = None
        self.history: list[tuple] = []
        self.future: list[tuple] = []
        self.material_source = find_maes(self.project)
        self.material_original = None
        self.maes_image = None
        self.maes_dirty = False
        self.material_draft: Path | None = None
        if self.material_source is not None:
            with Image.open(self.material_source) as raw:
                if not 0 < raw.width * raw.height <= MAX_PIXELS:
                    raise ValueError('Textura MAES excede o limite de segurança.')
                self.material_original = raw.convert('RGBA')
                self.maes_image = self.material_original.copy()
        self.restored_layers = self._restore_layers()
        self._compose()

    def _compose(self):
        result = self.base.copy()
        for layer in self.layers:
            if not layer.visible or layer.opacity <= 0:
                continue
            pixels = layer.pixels
            if layer.opacity < 100:
                pixels = pixels.copy()
                alpha = pixels.getchannel('A').point(lambda x: round(x*layer.opacity/100))
                pixels.putalpha(alpha)
            result = Image.alpha_composite(result, pixels)
        self.image = result

    def _compose_region(self, box):
        """Recompose only dirty rectangle while brushing; no 4K full repaint per move."""
        result=self.base.crop(box)
        for layer in self.layers:
            if not layer.visible or layer.opacity <= 0:
                continue
            pixels=layer.pixels.crop(box)
            if layer.opacity < 100:
                alpha=pixels.getchannel('A').point(
                    lambda value: round(value*layer.opacity/100))
                pixels.putalpha(alpha)
            result=Image.alpha_composite(result,pixels)
        self.image.paste(result,box)

    def _snapshot(self):
        return ([PaintLayer(layer.name, layer.pixels.copy(),
                            layer.visible, layer.opacity) for layer in self.layers],
                self.active_layer,
                self.selection.copy() if self.selection is not None else None,
                self.maes_image.copy() if self.maes_image is not None else None,
                self.maes_dirty)

    def _restore(self, snapshot):
        self.layers, self.active_layer, self.selection, self.maes_image, self.maes_dirty = snapshot
        self._compose()

    def checkpoint(self):
        self.history.append(self._snapshot())
        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)
        self.future.clear()

    def undo(self) -> bool:
        if not self.history:
            return False
        self.future.append(self._snapshot())
        self._restore(self.history.pop())
        return True

    def redo(self) -> bool:
        if not self.future:
            return False
        self.history.append(self._snapshot())
        self._restore(self.future.pop())
        return True

    def add_layer(self, name: str = 'Nova camada') -> int:
        if len(self.layers) >= self.layer_limit:
            raise ValueError(f'Limite de {self.layer_limit} camadas para esta resolução.')
        self.checkpoint()
        label = (name.strip() or 'Nova camada')[:45]
        self.layers.append(PaintLayer(label, Image.new('RGBA', self.image.size)))
        self.active_layer = len(self.layers)-1
        return self.active_layer

    def remove_layer(self):
        if len(self.layers) <= 1:
            raise ValueError('É necessário manter pelo menos uma camada.')
        self.checkpoint()
        self.layers.pop(self.active_layer)
        self.active_layer = min(self.active_layer, len(self.layers)-1)
        self._compose()

    def move_layer(self, step: int):
        index = self.active_layer + step
        if not 0 <= index < len(self.layers):
            return
        self.checkpoint()
        self.layers[self.active_layer], self.layers[index] = (
            self.layers[index], self.layers[self.active_layer])
        self.active_layer = index
        self._compose()

    def set_active(self, index: int):
        if not 0 <= index < len(self.layers):
            raise ValueError('Camada não encontrada.')
        self.active_layer = index

    def set_visible(self, visible: bool):
        self.checkpoint()
        self.layers[self.active_layer].visible = bool(visible)
        self._compose()

    def set_opacity(self, value: int):
        if not 0 <= value <= 100:
            raise ValueError('Opacidade da camada deve ficar entre 0 e 100.')
        if self.layers[self.active_layer].opacity == value:
            return
        self.checkpoint()
        self.layers[self.active_layer].opacity = value
        self._compose()

    def select_region(self, x: int, y: int, tolerance: int = 12) -> int:
        self.selection = _flood_mask(self.image, (x,y), tolerance)
        return self.selection.getbbox() is not None

    def clear_region(self):
        self.selection = None

    def _apply_mask(self, mask: Image.Image, xy: tuple[int,int], color: str,
                    opacity: float, erase: bool = False):
        if not math.isfinite(opacity) or not 0 < opacity <= 1:
            raise ValueError('Opacidade inválida.')
        if self.selection is not None:
            mask = ImageChops.multiply(mask, self.selection.crop(
                (xy[0],xy[1],xy[0]+mask.width,xy[1]+mask.height)))
        if opacity < 1:
            mask = mask.point(lambda a: round(a*opacity))
        if not mask.getbbox():
            return
        layer = self.layers[self.active_layer]
        box = (xy[0],xy[1],xy[0]+mask.width,xy[1]+mask.height)
        part = layer.pixels.crop(box)
        if erase:
            a = ImageChops.multiply(part.getchannel('A'),ImageOps.invert(mask))
            part.putalpha(a)
        else:
            pigment = Image.new('RGBA',mask.size,ImageColor.getrgb(color)+(255,))
            pigment.putalpha(mask)
            part = Image.alpha_composite(part,pigment)
        layer.pixels.paste(part,box)
        # Painting changes a small atlas rectangle: full compositing here
        # previously copied every pixel of every layer on each mouse motion.
        region=mask.getbbox()
        if region is not None:
            dirty=(box[0]+region[0],box[1]+region[1],
                   box[0]+region[2],box[1]+region[3])
            self._compose_region(dirty)

    def stroke(self, start: tuple[int,int], end: tuple[int,int],
               color: str, size: int = 18, opacity: float = 1.,
               erase: bool = False, hardness: float = 1.):
        if not isinstance(size,int) or not 1 <= size <= 256:
            raise ValueError('Pincel deve ter tamanho 1–256.')
        radius = max(1,size//2)
        x0,y0 = start
        x1,y1 = end
        left=max(0,min(x0,x1)-radius-2)
        top=max(0,min(y0,y1)-radius-2)
        right=min(self.image.width,max(x0,x1)+radius+3)
        bottom=min(self.image.height,max(y0,y1)+radius+3)
        if right <= left or bottom <= top:
            return
        gx,gy=np.meshgrid(np.arange(left,right),np.arange(top,bottom))
        mask=Image.fromarray(np.rint(255*coverage(
            segment_distance(gx,gy,start,end),radius,hardness)).astype(np.uint8))
        self._apply_mask(mask,(left,top),color,opacity,erase)

    def apply_surface_masks(self, patches, color: str, opacity: float = 1.,
                            erase: bool = False):
        """Merge face patches by maximum coverage before painting atlas tiles.

        Adjacent triangles share boundary texels: applying independently would
        double opacity there. Tiles also avoid recomposing a full 4K atlas.
        """
        tiles = {}
        tile_size = 128
        for mask,(x,y) in patches:
            if mask.mode != 'L' or x < 0 or y < 0 or x+mask.width > self.image.width or y+mask.height > self.image.height:
                raise ValueError('Máscara de superfície fora da textura.')
            for top in range(y//tile_size*tile_size,y+mask.height,tile_size):
                for left in range(x//tile_size*tile_size,x+mask.width,tile_size):
                    key=(left,top)
                    tile=tiles.setdefault(key,Image.new('L',(
                        min(tile_size,self.image.width-left),
                        min(tile_size,self.image.height-top))))
                    box=(max(x,left),max(y,top),
                         min(x+mask.width,left+tile.width),
                         min(y+mask.height,top+tile.height))
                    target=(box[0]-left,box[1]-top,box[2]-left,box[3]-top)
                    source=(box[0]-x,box[1]-y,box[2]-x,box[3]-y)
                    tile.paste(ImageChops.lighter(tile.crop(target),mask.crop(source)),target)
        for origin,mask in tiles.items():
            self._apply_mask(mask,origin,color,opacity,erase)

    def stamp(self, x: int, y: int, color: str, diameter: int = 48,
              opacity: float = 1.0, shape: str = 'Estrela',
              custom: Image.Image | None = None):
        """Stamp a color-tinted 2D mask onto the current Albedo layer.

        Works with a picked 3D surface UV or directly on the atlas. Uses the
        same undo/layer/region-selection rules as the existing brush.
        """
        if not 4 <= diameter <= 512:
            raise ValueError('Carimbo deve ter tamanho entre 4 e 512.')
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            return
        mask=stamp_mask(diameter,shape,custom)
        left=x-diameter//2
        top=y-diameter//2
        right=left+diameter
        bottom=top+diameter
        clipped=(max(0,left),max(0,top),
                 min(self.image.width,right),min(self.image.height,bottom))
        if clipped[0]>=clipped[2] or clipped[1]>=clipped[3]:
            return
        tile=mask.crop((clipped[0]-left,clipped[1]-top,
                        clipped[2]-left,clipped[3]-top))
        self._apply_mask(tile,(clipped[0],clipped[1]),color,opacity)

    def bucket(self, x: int, y: int, color: str, tolerance: int = 12):
        mask = self.selection if self.selection is not None else _flood_mask(
            self.image,(x,y),tolerance)
        self._apply_mask(mask,(0,0),color,1.0)

    def apply_material(self, name: str):
        """Modify MAES *data* channels ONLY within an explicit selected region."""
        if name not in PRESETS:
            raise ValueError('Material desconhecido.')
        self.apply_material_values(PRESETS[name])

    def apply_material_values(self, values):
        """Apply configurable metallic/AO/emissive/smoothness data, with undo."""
        if len(values) != 4 or any(not isinstance(v,int) or not 0 <= v <= 255 for v in values):
            raise ValueError('Canais do material devem ficar entre 0 e 255.')
        if self.maes_image is None:
            raise FileNotFoundError('Nenhum MAES.png encontrado. Converta a miniatura antes.')
        if self.selection is None or not self.selection.getbbox():
            raise ValueError('Selecione uma região da miniatura antes de aplicar o material.')
        self.checkpoint()
        coverage = self.selection
        if coverage.size != self.maes_image.size:
            coverage = coverage.resize(self.maes_image.size,Image.Resampling.NEAREST)
        value=Image.new('RGBA',self.maes_image.size,tuple(values))
        self.maes_image=Image.composite(value,self.maes_image,coverage)
        self.maes_dirty = True

    def save_draft(self, project: str | Path) -> Path:
        out = super().save_draft(project)
        paint_dir=out.parent
        if paint_dir.is_symlink():
            raise ValueError('Diretório de pintura inseguro.')
        layers_dir=paint_dir/'camadas'
        if layers_dir.is_symlink():
            raise ValueError('Diretório de camadas inseguro.')
        layers_dir.mkdir(exist_ok=True)
        descriptions=[]
        for index, layer in enumerate(self.layers):
            filename=f'camada_{index+1:02d}.png'
            target=layers_dir/filename
            if target.is_symlink():
                raise ValueError('Arquivo de camada inseguro.')
            _write_png(layer.pixels,target)
            descriptions.append({'name':layer.name,'file':filename,
                                 'visible':layer.visible,'opacity':layer.opacity})
        record={
            'schema':'astronyx-layers-v2',
            'source_sha256':_source_digest(self.original),
            'size':list(self.original.size),
            'active':self.active_layer,
            'layers':descriptions,
            'maes_dirty':bool(self.maes_dirty),
        }
        (paint_dir/'camadas.json').write_text(
            json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        if self.maes_dirty and self.maes_image is not None:
            self.material_draft=paint_dir/'MAES_editado.png'
            if self.material_draft.is_symlink():
                raise ValueError('Rascunho de material inseguro.')
            _write_png(self.maes_image,self.material_draft)
        return out

    def _restore_layers(self) -> bool:
        folder=self.project/'Pintura'
        manifest=folder/'camadas.json'
        if not manifest.is_file() or manifest.is_symlink():
            return False
        try:
            data=json.loads(manifest.read_text(encoding='utf-8'))
            items=data['layers']
            if (data.get('schema')!='astronyx-layers-v2'
                    or data.get('source_sha256')!=_source_digest(self.original)
                    or data.get('size')!=list(self.original.size)
                    or not isinstance(items,list) or not 1<=len(items)<=self.layer_limit):
                return False
            restored=[]
            for i,item in enumerate(items):
                expected=f'camada_{i+1:02d}.png'
                if item['file']!=expected:
                    return False
                image_path=folder/'camadas'/expected
                if image_path.is_symlink():
                    return False
                with Image.open(image_path) as raw:
                    if raw.size!=self.original.size:
                        return False
                    picture=raw.convert('RGBA')
                restored.append(PaintLayer(str(item.get('name','Camada'))[:45],picture,
                                           bool(item.get('visible',True)),
                                           max(0,min(100,int(item.get('opacity',100))))))
            active=int(data.get('active',0))
            if not 0<=active<len(restored):
                return False
            self.layers=restored
            self.active_layer=active
            # Restore MAES only when the matching draft belongs to this project.
            p=folder/'MAES_editado.png'
            if (self.maes_image is not None and data.get('maes_dirty')
                    and p.is_file() and not p.is_symlink()):
                with Image.open(p) as raw:
                    if raw.size == self.maes_image.size:
                        self.maes_image=raw.convert('RGBA')
                        self.maes_dirty=True
            return True
        except (OSError,KeyError,ValueError,TypeError):
            return False


def apply_materials_to_export(project: str | Path, albedo_draft: str | Path,
                              maes_draft: str | Path | None = None) -> list[Path]:
    """Apply both atlases with preflight, per-target backups and rollback on error."""
    root=_project(project)
    draft_dir=(root/'Pintura').resolve()
    sources=[(Path(albedo_draft), 'Albedo_editado.png', (
        'TaleWeaverLite/Albedo.png','TaleWeaverCmd_Source/Albedo.png',
        'Entrada_TaleWeaverCmd/albedo.png'))]
    if maes_draft is not None:
        sources.append((Path(maes_draft),'MAES_editado.png',(
            'TaleWeaverLite/MAES.png','TaleWeaverCmd_Source/MAES.png',
            'Entrada_TaleWeaverCmd/metallic_ao_emis_smoothness.png')))
    jobs=[]
    for draft,name,relative_targets in sources:
        if (draft.name!=name or draft.is_symlink()
                or not draft.is_file() or draft.resolve().parent!=draft_dir):
            raise ValueError('Rascunho de pintura fora da pasta permitida.')
        with Image.open(draft) as im:
            if not 0 < im.width*im.height <= MAX_PIXELS:
                raise ValueError('Textura de rascunho inválida.')
            paint=im.convert('RGBA')
        targets=[root/item for item in relative_targets if (root/item).is_file()]
        if not targets:
            raise FileNotFoundError(f'Não existe textura de destino para {name}.')
        for target in targets:
            if (target.is_symlink() or target.parent.is_symlink()
                    or not target.resolve().is_relative_to(root)):
                raise ValueError('Destino de pintura inseguro.')
            adjusted=paint
            if target.parent.name=='Entrada_TaleWeaverCmd' and max(paint.size)>2048:
                adjusted=paint.copy()
                adjusted.thumbnail((2048,2048),Image.Resampling.LANCZOS)
            jobs.append((target,adjusted))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backups=[]
    try:
        for target,_ in jobs:
            backup=target.with_name(f'{target.name}.{stamp}.bak')
            shutil.copy2(target,backup)
            backups.append((target,backup))
        for target,image in jobs:
            _write_png(image,target)
    except Exception:
        # Retain backups even after restoring so recovery remains possible.
        for target,backup in backups:
            if backup.is_file():
                shutil.copy2(backup,target)
        raise
    return [target for target,_ in jobs]
