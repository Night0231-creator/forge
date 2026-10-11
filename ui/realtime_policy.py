"""Bounded rendering and texture damage; no GUI or GPU dependency."""
from __future__ import annotations

import math


class FrameBudget:
    """Event-driven viewport: throttle interaction, never render while idle."""
    def __init__(self, fps=30, quality='Auto'):
        self.fps = fps
        self.quality = quality
        self.scale = 1.0
        self.last_frame = -1.0
        self.samples = []

    def configure(self, fps, quality):
        if fps not in (30, 60) or quality not in ('Auto', 'Leve', 'Alta'):
            raise ValueError('Perfil de visualização inválido.')
        self.fps, self.quality = fps, quality
        self.scale = .65 if quality == 'Leve' else 1.0
        self.samples.clear()

    def delay_ms(self, now):
        return max(0, math.ceil((self.last_frame + 1/self.fps - now)*1000))

    def record(self, now, milliseconds):
        self.last_frame = now
        if self.quality != 'Auto':
            return
        self.samples.append(milliseconds)
        if len(self.samples) < 12:
            return
        average = sum(self.samples)/len(self.samples)
        self.samples.clear()
        budget = 1000/self.fps
        if average > budget*.85:
            self.scale = max(.5, self.scale-.1)
        elif average < budget*.45:
            self.scale = min(1.0, self.scale+.05)


class TextureDamage:
    """Accumulate changed 128px tiles until the preview consumes them."""
    def __init__(self, size, tile=128):
        self.size, self.tile = size, tile
        self.full = True
        self.tiles = set()

    def mark(self, box=None):
        if box is None:
            self.full = True
            self.tiles.clear()
            return
        if self.full:
            return
        w, h = self.size
        left, top, right, bottom = box
        left, top = max(0, left), max(0, top)
        right, bottom = min(w, right), min(h, bottom)
        if right <= left or bottom <= top:
            return
        for y in range(top//self.tile, (bottom-1)//self.tile+1):
            for x in range(left//self.tile, (right-1)//self.tile+1):
                self.tiles.add((x, y))
        if len(self.tiles) > 256:
            self.mark()

    def consume(self):
        if self.full:
            result = None  # full upload
        else:
            w, h = self.size
            result = [(x*self.tile, y*self.tile,
                       min(w, (x+1)*self.tile), min(h, (y+1)*self.tile))
                      for x, y in sorted(self.tiles)]
        self.full = False
        self.tiles.clear()
        return result
