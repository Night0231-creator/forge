"""Prepare bounded, immutable preview patches on the editing worker."""
from dataclasses import dataclass
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


class PaintUpdates:
    def __init__(self,session,maximum=2048):
        self.session = session
        self.size = preview_size(session.image.size,maximum)
        self.image = None
        self.selection_source = None
        self.selection = None

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
        maes = None
        if materials and session.maes_image is not None:
            size = preview_size(session.maes_image.size,2048)
            # Alpha stores smoothness, so resample all four data channels
            # independently rather than premultiplying RGB by visual alpha.
            channels = [channel.resize(size,Image.Resampling.BILINEAR)
                        for channel in session.maes_image.split()]
            maes = np.asarray(Image.merge('RGBA',channels)).copy()
        return PaintUpdate(full,patches,self.selection,maes,materials)
