"""Fast offline geometry preview using only Tkinter. No textures in 3D view."""
from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from .geometry import inspect_obj


class ObjViewer(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg='#0C1020', highlightthickness=0, **kwargs)
        self.stats = None
        self.vertices = []
        self.faces = []
        self.yaw = 0.5
        self.pitch = 0.25
        self.zoom = 1.0
        self.last_mouse = None
        self.bind('<ButtonPress-1>', self._start_drag)
        self.bind('<B1-Motion>', self._drag)
        self.bind('<MouseWheel>', self._wheel)
        self.bind('<Button-4>', lambda _e: self._zoom(1.14))
        self.bind('<Button-5>', lambda _e: self._zoom(1/1.14))
        self.bind('<Configure>', lambda _e: self.render())
        self.render()

    def open(self, file: Path):
        self.stats, self.vertices, self.faces = inspect_obj(file, max_faces=1600)
        self.yaw, self.pitch, self.zoom = .5, .24, 1.0
        self.render()

    def _start_drag(self, event):
        self.last_mouse = (event.x, event.y)

    def _drag(self, event):
        if self.last_mouse:
            dx, dy = event.x-self.last_mouse[0], event.y-self.last_mouse[1]
            self.yaw += dx * .012
            self.pitch = max(-1.3, min(1.3, self.pitch + dy*.009))
        self.last_mouse = event.x, event.y
        self.render()

    def _wheel(self, event):
        self._zoom(1.13 if event.delta > 0 else 1/1.13)

    def _zoom(self, factor):
        self.zoom = max(.25, min(5, self.zoom*factor))
        self.render()

    def reset(self):
        self.yaw, self.pitch, self.zoom = .5, .24, 1.0
        self.render()

    def _project(self, xyz, width, height, center, units):
        x, y, z = (xyz[i] - center[i] for i in range(3))
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        rx, rz = cy*x - sy*z, sy*x + cy*z
        ry, depth = cp*y - sp*rz, sp*y + cp*rz
        return (width*.5 + rx*units, height*.55 - ry*units, depth)

    def render(self):
        self.delete('all')
        width, height = max(self.winfo_width(), 280), max(self.winfo_height(), 280)
        self.create_rectangle(0, 0, width, height, fill='#101626', outline='')
        # Faint reference axes / ground lines. Geometry is always fit to view.
        if not self.stats:
            self.create_text(width//2, height//2, text='Abra um OBJ ja preparado\npara visualizar e girar o personagem',
                             fill='#C5B6E7', font=('Segoe UI', 12), justify='center')
            return
        lo, hi = self.stats.min_xyz, self.stats.max_xyz
        center = tuple((lo[i]+hi[i])/2 for i in range(3))
        span = max(hi[i]-lo[i] for i in range(3))
        units = min(width*.62, height*.74)/max(span, 1e-5)*self.zoom
        def project(point):
            return self._project(point,width,height,center,units)
        # Disc of a ground reference plane at the Y minimum.
        radius = max(hi[0]-lo[0],hi[2]-lo[2])*.68
        center_ground = ((lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2)
        pts = []
        for i in range(33):
            t = i * 2*math.pi/32
            v = (center_ground[0]+radius*math.cos(t), center_ground[1], center_ground[2]+radius*math.sin(t))
            pts.extend(project(v)[:2])
        self.create_polygon(pts, outline='#46495F', fill='#191E2C', width=1)
        draw_faces = []
        for ids in self.faces:
            if len(ids) < 3:
                continue
            # Painter's algorithm: flat shaded silhouette for fast, offline preview.
            try:
                projected = [project(self.vertices[i]) for i in ids[:7]]
            except IndexError:
                continue
            x1,y1,z1 = self.vertices[ids[0]]
            x2,y2,z2 = self.vertices[ids[1]]
            x3,y3,z3 = self.vertices[ids[2]]
            ux,uy,uz = x2-x1,y2-y1,z2-z1
            vx,vy,vz = x3-x1,y3-y1,z3-z1
            nx,ny,nz = uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
            norm = max(math.sqrt(nx*nx+ny*ny+nz*nz),1e-10)
            light = abs((nx*.4+ny*.7+nz*.5)/norm)
            brightness = int(72 + 95*light)
            color=f'#{int(brightness*.73):02x}{int(brightness*.75):02x}{brightness:02x}'
            coords = [v for p in projected for v in p[:2]]
            draw_faces.append((sum(p[2] for p in projected)/len(projected),coords,color))
        for _,coords,color in sorted(draw_faces, reverse=True):
            self.create_polygon(coords, fill=color, outline='#222940', width=0.35)
        self.create_text(15, 14, anchor='nw', text=f'{self.stats.vertices:,} vertices  |  {self.stats.faces:,} faces',
                         fill='#EEE7FF', font=('Consolas',10))
        self.create_text(15, height-16, anchor='sw',
                         text=f'Altura OBJ: {self.stats.height:.3f} un.  |  Arraste para girar  ·  Roda para zoom',
                         fill='#B8C0DF', font=('Segoe UI',10))
