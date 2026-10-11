"""Offline OBJ UV/albedo preview rasterizer. Not part of TaleSpire export.

Dependencies (preview only): Pillow + numpy. No Blender, network or shader
dependencies. Prepared Y-up OBJ, one atlas, opaque triangles. No PBR lighting.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageOps

from .size_reference import paint_reference

MAX_TRIANGLES = 150000
MAX_TEXTURE_PIXELS = 4096 * 4096


class PreviewError(ValueError):
    pass


@dataclass(frozen=True)
class TextureMesh:
    points: np.ndarray
    triangles: np.ndarray
    texcoords: np.ndarray
    texture_path: Path
    limited: bool = False


def albedo_for(obj: Path) -> Path | None:
    obj = Path(obj)
    for candidate in (
        obj.parent / 'Albedo.png',
        obj.parent / 'albedo.png',
        obj.parent / f'{obj.stem}.png',
        obj.parent.parent / 'TaleWeaverLite' / 'Albedo.png',
    ):
        if candidate.is_file():
            return candidate
    return None


def load_obj(path: Path, limit: int = MAX_TRIANGLES) -> TextureMesh:
    path = Path(path)
    tex = albedo_for(path)
    if tex is None:
        raise PreviewError('Não foi encontrada a textura Albedo.png ao lado do OBJ.')
    vertices, uvs, faces, face_uvs = [], [], [], []
    clipped = False

    def index(raw: str, size: int) -> int:
        num = int(raw)
        idx = (num - 1) if num > 0 else (size + num)
        if num == 0 or idx < 0 or idx >= size:
            raise IndexError('Índice OBJ fora do intervalo')
        return idx

    with path.open('r', encoding='utf-8-sig', errors='replace') as obj:
        for line in obj:
            if line.startswith('v '):
                parts = line.split()
                if len(parts) >= 4:
                    xyz = tuple(float(x) for x in parts[1:4])
                    if all(math.isfinite(x) for x in xyz):
                        vertices.append(xyz)
            elif line.startswith('vt '):
                parts = line.split()
                if len(parts) >= 3:
                    uv = tuple(float(x) for x in parts[1:3])
                    if all(math.isfinite(x) for x in uv):
                        uvs.append(uv)
            elif line.startswith('f '):
                parts = line.split()[1:]
                try:
                    corners = [(index(p.split('/')[0], len(vertices)),
                                index(p.split('/')[1], len(uvs))) for p in parts]
                except (IndexError, ValueError, KeyError):
                    continue
                for k in range(1, len(corners)-1):
                    if len(faces) >= limit:
                        clipped = True
                        break
                    tri = (corners[0], corners[k], corners[k+1])
                    faces.append(tuple(t[0] for t in tri))
                    face_uvs.append(tuple(uvs[t[1]] for t in tri))
                if clipped:
                    break
    if not vertices or not faces:
        raise PreviewError('O OBJ não possui faces com coordenadas UV válidas.')
    return TextureMesh(
        np.asarray(vertices, dtype=np.float32),
        np.asarray(faces, dtype=np.int32),
        np.asarray(face_uvs, dtype=np.float32),
        tex, clipped
    )


def read_albedo(path: Path, max_side: int = 1024) -> np.ndarray:
    with Image.open(path) as raw:
        if raw.width * raw.height > MAX_TEXTURE_PIXELS:
            raise PreviewError('Textura de prévia excede o limite de segurança.')
        image = ImageOps.exif_transpose(raw).convert('RGB')
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return np.asarray(image, dtype=np.uint8)


def draw(mesh: TextureMesh, albedo: np.ndarray, yaw: float, pitch: float,
         zoom: float, width: int, height: int, pan_x: float = 0,
         pan_y: float = 0, wire: bool = False,
         show_reference: bool = False, reference_height: float = 1.75) -> Image.Image:
    """CPU preview: orthographic barycentric UV, nearest sampling, Z buffer.

    Returns Pillow image. UI layer displays it through ImageTk on the Tk thread.
    """
    width = int(max(100, min(width, 900)))
    height = int(max(100, min(height, 900)))
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[:] = (17, 21, 34)
    depth = np.full((height, width), -np.inf, dtype=np.float32)

    points = mesh.points.astype(np.float64, copy=False)
    lo = points.min(axis=0)
    hi = points.max(axis=0)
    if show_reference and (not math.isfinite(reference_height) or reference_height <= 0):
        raise PreviewError('Altura de referencia invalida.')
    extent = max(float((hi-lo).max()), reference_height if show_reference else 0.0, 1e-5)
    coords = points-(lo+hi)*0.5
    c, s = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x = c*coords[:, 0] - s*coords[:, 2]
    z = s*coords[:, 0] + c*coords[:, 2]
    y = cp*coords[:, 1] - sp*z
    d = sp*coords[:, 1] + cp*z
    # Reserve space at right for the 1x1 ruler; never rescale the mesh alone.
    unit = min(width * (.50 if show_reference else .62), height * .74)/extent*zoom
    px = width*(.37 if show_reference else .5)+x*unit+pan_x
    py = height*.55-y*unit+pan_y
    # Use a fixed light vector for legible material shading.
    light_dir = np.array([0.35, 0.75, 0.56])
    light_dir = light_dir / np.linalg.norm(light_dir)
    tw, th = albedo.shape[1], albedo.shape[0]

    for ids, uv in zip(mesh.triangles, mesh.texcoords):
        xs = px[ids]
        ys = py[ids]
        left = max(0, int(math.floor(float(xs.min()))))
        right = min(width-1, int(math.ceil(float(xs.max()))))
        top = max(0, int(math.floor(float(ys.min()))))
        bottom = min(height-1, int(math.ceil(float(ys.max()))))
        if right < left or bottom < top:
            continue
        x0, x1, x2 = xs
        y0, y1, y2 = ys
        area = (x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)
        if abs(float(area)) < 1e-8:
            continue
        gx, gy = np.meshgrid(np.arange(left,right+1,dtype=np.float32)+.5,
                            np.arange(top,bottom+1,dtype=np.float32)+.5)
        w0 = ((x1-gx)*(y2-gy)-(y1-gy)*(x2-gx))/area
        w1 = ((x2-gx)*(y0-gy)-(y2-gy)*(x0-gx))/area
        w2 = 1.0-w0-w1
        mask = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
        if not mask.any():
            continue
        dz = w0*d[ids[0]] + w1*d[ids[1]] + w2*d[ids[2]]
        slice_depth = depth[top:bottom+1,left:right+1]
        mask &= dz > slice_depth
        if not mask.any():
            continue
        u = w0*uv[0][0] + w1*uv[1][0] + w2*uv[2][0]
        v = w0*uv[0][1] + w1*uv[1][1] + w2*uv[2][1]
        # Bilinear albedo improves small textures, faces and armor in the preview.
        # Sampling is clamped to the image edges (no changes to exported UVs).
        tx = np.clip(u[mask]*(tw-1), 0, tw-1)
        ty = np.clip((1.0-v[mask])*(th-1), 0, th-1)
        ix, iy = tx.astype(np.int32), ty.astype(np.int32)
        ix1, iy1 = np.minimum(ix+1, tw-1), np.minimum(iy+1, th-1)
        fx, fy = (tx-ix)[:,None], (ty-iy)[:,None]
        c00 = albedo[iy, ix].astype(np.float32)
        c10 = albedo[iy, ix1].astype(np.float32)
        c01 = albedo[iy1, ix].astype(np.float32)
        c11 = albedo[iy1, ix1].astype(np.float32)
        filtered = (c00*(1-fx)*(1-fy) + c10*fx*(1-fy)
                    + c01*(1-fx)*fy + c11*fx*fy)
        tri_points = points[ids]
        normal = np.cross(tri_points[1]-tri_points[0],tri_points[2]-tri_points[0])
        nrm = float(np.linalg.norm(normal))
        shade = 0.67 + .33*abs(float(np.dot(normal,light_dir)/nrm)) if nrm>1e-10 else 1.0
        sample = np.clip(filtered*shade,0,255).astype(np.uint8)
        section = rgb[top:bottom+1,left:right+1]
        section[mask] = sample
        slice_depth[mask] = dz[mask].astype(np.float32)

    frame = Image.fromarray(rgb, mode='RGB')
    if show_reference:
        paint_reference(frame, base_y=float(lo[1]),
                        center_y=float((lo[1]+hi[1])*.5),
                        model_height=float(hi[1]-lo[1]),
                        pixels_per_unit=unit, pitch=pitch,
                        pan_x=pan_x, pan_y=pan_y,
                        reference_height=reference_height)
    return frame

def draw_fast(mesh: TextureMesh, albedo: np.ndarray, yaw: float, pitch: float,
              zoom: float, width: int, height: int, pan_x: float = 0,
              pan_y: float = 0, show_reference: bool = False,
              reference_height: float = 1.75) -> Image.Image:
    """Fast coloured CPU fallback for complex OBJ files.

    Painter-sort triangles, rasterize with Pillow's native polygon implementation
    and sample albedo at the UV centroid. Unlike skipping 97% of triangles, this
    preserves a solid silhouette even for high-poly Meshy models. The result is
    a faceted preview, not a substitute for GPU PBR or exact UV bilinear sampling.
    """
    from PIL import ImageDraw
    width=int(max(100,min(width,900)))
    height=int(max(100,min(height,900)))
    points=np.asarray(mesh.points,dtype=np.float64)
    if not len(mesh.triangles):
        raise PreviewError('Nenhuma face para pré-visualizar.')
    lo=points.min(axis=0)
    hi=points.max(axis=0)
    extent=max(float((hi-lo).max()),
               reference_height if show_reference else 0.0,1e-5)
    centered=points-(lo+hi)*.5
    c,s=math.cos(yaw),math.sin(yaw)
    cp,sp=math.cos(pitch),math.sin(pitch)
    rx=c*centered[:,0]-s*centered[:,2]
    rz=s*centered[:,0]+c*centered[:,2]
    ry=cp*centered[:,1]-sp*rz
    depth=sp*centered[:,1]+cp*rz
    unit=min(width*(.50 if show_reference else .62),height*.74)/extent*zoom
    projected=np.stack((width*(.37 if show_reference else .5)+rx*unit+pan_x,
                        height*.55-ry*unit+pan_y),axis=1)
    indices=mesh.triangles
    triangle_xy=projected[indices]
    triangle_depth=depth[indices].mean(axis=1)
    # Back-to-front order matches the depth convention used by draw().
    order=np.argsort(triangle_depth)
    uv=np.asarray(mesh.texcoords,dtype=np.float64).mean(axis=1)
    th,tw=albedo.shape[:2]
    tx=np.clip((uv[:,0]*(tw-1)).astype(np.int32),0,tw-1)
    ty=np.clip(((1-uv[:,1])*(th-1)).astype(np.int32),0,th-1)
    colors=albedo[ty,tx].astype(np.float32)
    # Bright but not flat: lighting measured in the rotated camera frame.
    triangles=points[indices]
    n=np.cross(triangles[:,1]-triangles[:,0],
               triangles[:,2]-triangles[:,0])
    norms=np.maximum(np.linalg.norm(n,axis=1),1e-8)
    light=np.abs((n @ np.array([.34,.75,.53]))/norms)
    brightness=(.76+.24*light)
    colors=np.clip(colors*brightness[:,None]+3,0,255).astype(np.uint8)
    visible=((triangle_xy[:,:,0].max(axis=1)>=0)
             &(triangle_xy[:,:,0].min(axis=1)<=width)
             &(triangle_xy[:,:,1].max(axis=1)>=0)
             &(triangle_xy[:,:,1].min(axis=1)<=height))
    frame=Image.new('RGB',(width,height),(24,28,42))
    painter=ImageDraw.Draw(frame)
    palette=[tuple(int(v) for v in px) for px in colors]
    for i in order:
        if not visible[i]:
            continue
        pts=triangle_xy[i]
        painter.polygon(((float(pts[0,0]),float(pts[0,1])),
                         (float(pts[1,0]),float(pts[1,1])),
                         (float(pts[2,0]),float(pts[2,1]))),
                        fill=palette[i])
    if show_reference:
        paint_reference(frame,base_y=float(lo[1]),
                        center_y=float((lo[1]+hi[1])*.5),
                        model_height=float(hi[1]-lo[1]),
                        pixels_per_unit=unit,pitch=pitch,
                        pan_x=pan_x,pan_y=pan_y,
                        reference_height=reference_height)
    return frame
