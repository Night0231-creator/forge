"""Project a screen brush onto every covered UV face with local depth testing.

Unlike stamping only the center hit UV, this maps the entire brush footprint
through each triangle. A stroke crosses UV seams without drawing between
islands. All returned patches are computed before applying the paint operation.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image
from core.brushes import coverage, segment_distance

MAX_WORK_PIXELS = 32 * 1024 * 1024


def _weights(x, y, xs, ys):
    area = (xs[1]-xs[0])*(ys[2]-ys[0]) - (ys[1]-ys[0])*(xs[2]-xs[0])
    if abs(float(area)) < 1e-12:
        return None
    a = ((xs[1]-x)*(ys[2]-y)-(ys[1]-y)*(xs[2]-x))/area
    b = ((xs[2]-x)*(ys[0]-y)-(ys[2]-y)*(xs[0]-x))/area
    return a, b, 1-a-b


def _clip(vertices, axis, boundary, lower):
    """Clip x/y/depth/u/v vertices against a screen rectangle edge."""
    if not len(vertices):
        return vertices
    result = []
    previous = vertices[-1]
    prev_inside = previous[axis] >= boundary if lower else previous[axis] <= boundary
    for current in vertices:
        inside = current[axis] >= boundary if lower else current[axis] <= boundary
        if inside != prev_inside:
            ratio = (boundary-previous[axis])/(current[axis]-previous[axis])
            result.append(previous + ratio*(current-previous))
        if inside:
            result.append(current)
        previous, prev_inside = current, inside
    return np.asarray(result)


def _front_faces(picker, candidates, bounds):
    left, top, right, bottom = bounds
    # Half-pixel screen sampling keeps seams narrow even in a 4K texture.
    width, height = (right-left)*2+1, (bottom-top)*2+1
    depth = np.full((height, width), -np.inf, dtype=np.float32)
    front = np.full((height, width), -1, dtype=np.int32)
    for triangle in candidates:
        xs, ys = picker.x[triangle], picker.y[triangle]
        x0 = max(0, int(math.floor((xs.min()-left)*2)))
        x1 = min(width-1, int(math.ceil((xs.max()-left)*2)))
        y0 = max(0, int(math.floor((ys.min()-top)*2)))
        y1 = min(height-1, int(math.ceil((ys.max()-top)*2)))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0,x1+1)*.5+left,
                            np.arange(y0,y1+1)*.5+top)
        bary = _weights(gx, gy, xs, ys)
        if bary is None:
            continue
        a, b, c = bary
        z = a*picker.depth[triangle,0]+b*picker.depth[triangle,1]+c*picker.depth[triangle,2]
        section = depth[y0:y1+1,x0:x1+1]
        inside = (a >= -1e-7)&(b >= -1e-7)&(c >= -1e-7)&(z > section)
        section[inside] = z[inside]
        front[y0:y1+1,x0:x1+1][inside] = triangle
    return front


def surface_masks(picker, start, end, texture_size, diameter=20,
                  hardness=1., paint_through=False, stencil=None):
    """Return (Pillow L mask, atlas origin) patches. Size is in screen pixels.

    Optional stencil (L) is projected in screen space for seam-aware stamps.
    Degenerate UVs are skipped. Coincident/overlapping UV islands necessarily
    share texture pixels; separate geometry cannot get independent colors there.
    """
    if (not all(math.isfinite(float(v)) for v in (*start,*end,diameter,hardness))
            or not 1 <= diameter <= 200 or not 0 <= hardness <= 1):
        raise ValueError('Pincel de superfície inválido.')
    width, height = texture_size
    if min(texture_size) < 2 or width*height > 4096*4096:
        raise ValueError('Textura inválida para pintura de superfície.')
    radius = diameter*.5
    # Bound each event's work; the UI samples long drags into short segments.
    if math.hypot(end[0]-start[0],end[1]-start[1]) > 250:
        raise ValueError('Divida o traço em segmentos menores.')
    left = max(0, int(math.floor(min(start[0],end[0])-radius-1)))
    right = min(picker.canvas_width, int(math.ceil(max(start[0],end[0])+radius+1)))
    top = max(0, int(math.floor(min(start[1],end[1])-radius-1)))
    bottom = min(picker.canvas_height, int(math.ceil(max(start[1],end[1])+radius+1)))
    if right <= left or bottom <= top:
        return []
    candidates = np.flatnonzero((picker.min_x <= right)&(picker.max_x >= left)
                                &(picker.min_y <= bottom)&(picker.max_y >= top)
                                &(np.abs(picker.area) > 1e-8))
    if not len(candidates):
        return []
    front = None if paint_through else _front_faces(picker,candidates,(left,top,right,bottom))
    stamp = None if stencil is None else np.asarray(stencil.convert('L'),dtype=np.uint8)
    patches, work = [], 0
    for triangle in candidates:
        uv = picker.uv[triangle]
        clipped = np.column_stack((picker.x[triangle],picker.y[triangle],
                                   picker.depth[triangle],uv))
        for axis,boundary,lower in ((0,left,True),(0,right,False),
                                    (1,top,True),(1,bottom,False)):
            clipped = _clip(clipped,axis,boundary,lower)
        if len(clipped) < 3:
            continue
        tx = clipped[:,3]*(width-1)
        ty = (1-clipped[:,4])*(height-1)
        x0 = max(0,int(math.floor(tx.min())))
        x1 = min(width-1,int(math.ceil(tx.max())))
        y0 = max(0,int(math.floor(ty.min())))
        y1 = min(height-1,int(math.ceil(ty.max())))
        if x1 < x0 or y1 < y0:
            continue
        work += (x1-x0+1)*(y1-y0+1)
        if work > MAX_WORK_PIXELS:
            raise ValueError('Aproxime o modelo ou reduza o pincel para pintar esta área.')
        us, vs = uv[:,0], uv[:,1]
        for tile_top in range(y0,y1+1,128):
            tile_bottom = min(y1+1,tile_top+128)
            u,v = np.meshgrid(np.arange(x0,x1+1)/(width-1),
                             1-np.arange(tile_top,tile_bottom)/(height-1))
            bary = _weights(u,v,us,vs)
            if bary is None:
                continue
            a,b,c = bary
            inside = (a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)
            px = a*picker.x[triangle,0]+b*picker.x[triangle,1]+c*picker.x[triangle,2]
            py = a*picker.y[triangle,0]+b*picker.y[triangle,1]+c*picker.y[triangle,2]
            alpha = (np.ones_like(px) if stamp is not None else
                     coverage(segment_distance(px,py,start,end),radius,hardness))
            inside &= (px>=left)&(px<=right)&(py>=top)&(py<=bottom)&(alpha>0)
            if not inside.any():
                continue
            if front is not None:
                ix = np.clip(np.rint((px-left)*2).astype(np.int32),0,front.shape[1]-1)
                iy = np.clip(np.rint((py-top)*2).astype(np.int32),0,front.shape[0]-1)
                nearest = front[iy,ix]
                ids = np.maximum(nearest,0)
                xs,ys = picker.x[ids],picker.y[ids]
                area = np.where(np.abs(picker.area[ids])>1e-12,picker.area[ids],1.)
                f0 = ((xs[...,1]-px)*(ys[...,2]-py)-(ys[...,1]-py)*(xs[...,2]-px))/area
                f1 = ((xs[...,2]-px)*(ys[...,0]-py)-(ys[...,2]-py)*(xs[...,0]-px))/area
                f2 = 1-f0-f1
                dz = (a*picker.depth[triangle,0]+b*picker.depth[triangle,1]+c*picker.depth[triangle,2])
                closest = (f0*picker.depth[ids,0]+f1*picker.depth[ids,1]+f2*picker.depth[ids,2])
                # Correct the sample's plane depth at each actual UV texel.
                valid_front = (nearest>=0)&(f0>=-1e-6)&(f1>=-1e-6)&(f2>=-1e-6)
                inside &= ~valid_front | (dz>=closest-1e-6)
            if stamp is not None:
                sx = (px-(start[0]-radius))/diameter
                sy = (py-(start[1]-radius))/diameter
                inside &= (sx>=0)&(sx<=1)&(sy>=0)&(sy<=1)
                stamp_x = np.clip(np.rint(sx*(stamp.shape[1]-1)).astype(np.int32),0,stamp.shape[1]-1)
                stamp_y = np.clip(np.rint(sy*(stamp.shape[0]-1)).astype(np.int32),0,stamp.shape[0]-1)
                alpha = stamp[stamp_y,stamp_x].astype(np.float32)/255
            mask = np.where(inside,np.rint(alpha*255),0).astype(np.uint8)
            image = Image.fromarray(mask)
            box = image.getbbox()
            if box:
                patches.append((image.crop(box),(x0+box[0],tile_top+box[1])))
    return patches
