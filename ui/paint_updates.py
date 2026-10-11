"""Prepare bounded, immutable preview patches on the editing worker."""
from dataclasses import dataclass, field
import math
from PIL import Image
import numpy as np
from .realtime_viewer import preview_size, texture_patch


@dataclass
class PaintUpdate:
    full: object
    patches: list
    selection: object
    materials: object = None
    material_changed: bool = False
    material_patches: list = field(default_factory=list)


class PaintUpdates:
    def __init__(self,session,maximum=2048):
        self.session = session
        self.size = preview_size(session.image.size,maximum)
        self.image = None
        self.selection_source = None
        self.selection = None
        self.materials = None

    def _materials(self,force=False):
        source=self.session.maes_image
        damage=self.session.material_damage
        if source is None or damage is None:
            return None,[],False
        boxes=damage.consume()
        size=preview_size(source.size,2048)
        if force or boxes is None or self.materials is None or self.materials.size!=size:
            # All four channels store data; do not premultiply by smoothness.
            self.materials=Image.merge('RGBA',[
                channel.resize(size,Image.Resampling.BILINEAR) for channel in source.split()])
            return np.asarray(self.materials).copy(),[],True
        patches=[]
        sw,sh=source.size
        tw,th=size
        for box in boxes:
            mapped=(max(0,math.floor(box[0]*tw/sw)-2),
                    max(0,math.floor(box[1]*th/sh)-2),
                    min(tw,math.ceil(box[2]*tw/sw)+2),
                    min(th,math.ceil(box[3]*th/sh)+2))
            x0,y0,x1,y1=mapped
            # Crop a bounded source halo before splitting; avoid copying four
            # complete 4K channels on every material brush movement.
            bounds=(max(0,math.floor(x0*sw/tw)-2),max(0,math.floor(y0*sh/th)-2),
                    min(sw,math.ceil(x1*sw/tw)+2),min(sh,math.ceil(y1*sh/th)+2))
            sample=(x0*sw/tw-bounds[0],y0*sh/th-bounds[1],
                    x1*sw/tw-bounds[0],y1*sh/th-bounds[1])
            patch=Image.merge('RGBA',[
                channel.resize((x1-x0,y1-y0),Image.Resampling.BILINEAR,box=sample)
                for channel in source.crop(bounds).split()])
            self.materials.paste(patch,mapped)
            patches.append((mapped,np.asarray(patch).copy()))
        return None,patches,bool(patches)

    def prepare(self, *, materials=False):
        session = self.session
        damage = session.preview_damage.consume()
        full,patches = None,[]
        if self.image is None or damage is None:
            self.image = session.image.resize(self.size,Image.Resampling.BILINEAR).convert('RGB')
            full = self.image.copy()
        else:
            for box in damage:
                mapped,data = texture_patch(session.image,self.size,box)
                patch = Image.fromarray(data)
                self.image.paste(patch,mapped)
                patches.append((mapped,patch))
        if session.selection is not self.selection_source:
            self.selection_source = session.selection
            self.selection = (None if session.selection is None else
                              session.selection.resize(self.size,Image.Resampling.NEAREST))
        maes,material_patches,changed=self._materials(materials)
        return PaintUpdate(full,patches,self.selection,maes,changed,material_patches)
