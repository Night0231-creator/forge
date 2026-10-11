"""CPU screen-space picking of the visible OBJ triangle to paint its UV atlas.

Uses EXACTLY the orthographic camera convention of ui.texture_renderer.draw.
No fake 3D brush: mouse clicks select a visible projected mesh triangle, then
barycentric interpolation maps the hit to source albedo UV coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from .studio_scene import PREVIEW_LIMIT


@dataclass(frozen=True)
class SurfaceHit:
    u: float
    v: float
    depth: float
    triangle: int

    def pixel(self, width: int, height: int) -> tuple[int, int]:
        if width < 1 or height < 1:
            raise ValueError('Dimensões de textura inválidas.')
        return (
            int(round(min(1.0,max(0.0,self.u))*(width-1))),
            int(round((1.0-min(1.0,max(0.0,self.v)))*(height-1))),
        )


class ProjectedUVPicker:
    """Projection snapshot: rebuild when the camera/view size changes.

    All primitive polygons and UVs are read-only; a hit never changes geometry.
    The frontmost triangle is chosen using the SAME maximal camera-depth rule
    as the texture renderer, even when multiple faces overlap onscreen.
    """
    def __init__(self, mesh, *, yaw: float, pitch: float, zoom: float,
                 canvas_width: int, canvas_height: int,
                 pan_x: float = 0., pan_y: float = 0.,
                 show_reference: bool = True, reference_height: float = 1.75):
        if canvas_width < 100 or canvas_height < 100:
            raise ValueError('Visualização pequena demais para pintura 3D.')
        if not (all(math.isfinite(float(v)) for v in
                    (yaw,pitch,zoom,pan_x,pan_y,reference_height))
                and zoom > 0 and reference_height > 0):
            raise ValueError('Câmera inválida para pintura 3D.')
        self.canvas_width, self.canvas_height = canvas_width, canvas_height
        self.image_width = min(PREVIEW_LIMIT,max(160,canvas_width))
        self.image_height = min(PREVIEW_LIMIT,max(160,canvas_height))
        self.offset_x=(canvas_width-self.image_width)*0.5
        self.offset_y=(canvas_height-self.image_height)*0.5

        points=np.asarray(mesh.points,dtype=np.float64)
        triangles=np.asarray(mesh.triangles,dtype=np.int32)
        uv=np.asarray(mesh.texcoords,dtype=np.float64)
        if (points.ndim!=2 or points.shape[1]!=3
                or triangles.ndim!=2 or triangles.shape[1]!=3
                or uv.shape!=(len(triangles),3,2) or not len(triangles)):
            raise ValueError('Malha não triangulada ou sem UVs.')
        if not np.isfinite(points).all() or not np.isfinite(uv).all():
            raise ValueError('Vértices ou UVs inválidos.')
        low=points.min(axis=0)
        high=points.max(axis=0)
        extent=max(float((high-low).max()),
                   reference_height if show_reference else 0.0,1e-5)
        centered=points-(low+high)*.5
        c,s=math.cos(yaw),math.sin(yaw)
        cp,sp=math.cos(pitch),math.sin(pitch)
        rotated_x=c*centered[:,0]-s*centered[:,2]
        rotated_z=s*centered[:,0]+c*centered[:,2]
        rotated_y=cp*centered[:,1]-sp*rotated_z
        depths=sp*centered[:,1]+cp*rotated_z
        unit=min(self.image_width*(.50 if show_reference else .62),
                 self.image_height*.74)/extent*zoom
        x=self.offset_x + self.image_width*(.37 if show_reference else .5)+rotated_x*unit+pan_x
        y=self.offset_y + self.image_height*.55-rotated_y*unit+pan_y

        # Cache camera-space projected triangles; no Python loop per mouse move.
        self.x=x[triangles]
        self.y=y[triangles]
        self.depth=depths[triangles]
        self.uv=uv
        self.area=((self.x[:,1]-self.x[:,0])*(self.y[:,2]-self.y[:,0])
                   -(self.y[:,1]-self.y[:,0])*(self.x[:,2]-self.x[:,0]))
        self.min_x=self.x.min(axis=1)
        self.max_x=self.x.max(axis=1)
        self.min_y=self.y.min(axis=1)
        self.max_y=self.y.max(axis=1)

    def hit(self, canvas_x: float, canvas_y: float) -> SurfaceHit | None:
        if not (math.isfinite(canvas_x) and math.isfinite(canvas_y)):
            return None
        valid=((self.min_x<=canvas_x) & (self.max_x>=canvas_x)
               & (self.min_y<=canvas_y) & (self.max_y>=canvas_y)
               & (np.abs(self.area)>1e-8))
        candidates=np.flatnonzero(valid)
        if not len(candidates):
            return None
        xs=self.x[candidates]
        ys=self.y[candidates]
        area=self.area[candidates]
        w0=((xs[:,1]-canvas_x)*(ys[:,2]-canvas_y)
            -(ys[:,1]-canvas_y)*(xs[:,2]-canvas_x))/area
        w1=((xs[:,2]-canvas_x)*(ys[:,0]-canvas_y)
            -(ys[:,2]-canvas_y)*(xs[:,0]-canvas_x))/area
        w2=1.0-w0-w1
        inside=(w0>=-1e-5)&(w1>=-1e-5)&(w2>=-1e-5)
        if not inside.any():
            return None
        candidates=candidates[inside]
        weights=np.stack((w0[inside],w1[inside],w2[inside]),axis=1)
        depths=(self.depth[candidates]*weights).sum(axis=1)
        chosen=int(np.argmax(depths))
        tri=int(candidates[chosen])
        hit_uv=(self.uv[tri]*weights[chosen,:,None]).sum(axis=0)
        return SurfaceHit(float(hit_uv[0]),float(hit_uv[1]),
                          float(depths[chosen]),tri)
