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


def _raster_blocks(candidates, bounds, batch=65536):
    """Raster coordinates in bounded NumPy batches, rather than per face."""
    x0, y0, x1, y1 = bounds.T
    widths = x1-x0+1
    counts = widths*(y1-y0+1)
    ends = np.cumsum(counts)
    starts = ends-counts
    for offset in range(0, int(ends[-1]), batch):
        index = np.arange(offset, min(offset+batch, int(ends[-1])))
        face = np.searchsorted(ends, index, side='right')
        local = index-starts[face]
        yield candidates[face], x0[face]+local % widths[face], y0[face]+local//widths[face]


def _batch_weights(x, y, xs, ys, area):
    a = ((xs[:,1]-x)*(ys[:,2]-y)-(ys[:,1]-y)*(xs[:,2]-x))/area
    b = ((xs[:,2]-x)*(ys[:,0]-y)-(ys[:,2]-y)*(xs[:,0]-x))/area
    return a, b, 1-a-b


def _front_batched(picker, candidates, bounds):
    left, top, right, bottom = bounds
    width, height = (right-left)*2+1, (bottom-top)*2+1
    depth = np.full(width*height, -np.inf)
    front = np.full(width*height, len(picker.x), dtype=np.int32)
    boxes = np.column_stack((
        np.maximum(0, np.floor((picker.min_x[candidates]-left)*2)),
        np.maximum(0, np.floor((picker.min_y[candidates]-top)*2)),
        np.minimum(width-1, np.ceil((picker.max_x[candidates]-left)*2)),
        np.minimum(height-1, np.ceil((picker.max_y[candidates]-top)*2)),
    )).astype(np.int64)
    for ids, x, y in _raster_blocks(candidates, boxes):
        a,b,c = _batch_weights(x*.5+left, y*.5+top, picker.x[ids], picker.y[ids], picker.area[ids])
        inside = (a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)
        ids, index = ids[inside], (y*width+x)[inside]
        z = (a[inside]*picker.depth[ids,0]+b[inside]*picker.depth[ids,1]+c[inside]*picker.depth[ids,2])
        old = depth[index].copy()
        np.maximum.at(depth, index, z)
        # Clear an earlier face only when this batch actually advances depth.
        front[index[depth[index]>old]] = len(picker.x)
        winners = z == depth[index]
        np.minimum.at(front, index[winners], ids[winners])
    front[front == len(picker.x)] = -1
    return front.reshape(height,width)


def _clipped_bounds(picker, candidates, bounds, size):
    """UV bounds of a triangle/brush rectangle intersection, in parallel."""
    left, top, right, bottom = bounds
    screen = np.stack((picker.x[candidates],picker.y[candidates]),axis=-1)
    uv = picker.uv[candidates]
    valid = ((screen[:,:,0]>=left)&(screen[:,:,0]<=right)
             &(screen[:,:,1]>=top)&(screen[:,:,1]<=bottom))
    low = np.min(np.where(valid[:,:,None],uv,np.inf),axis=1)
    high = np.max(np.where(valid[:,:,None],uv,-np.inf),axis=1)
    following, next_uv = np.roll(screen,-1,axis=1), np.roll(uv,-1,axis=1)
    for axis, boundary, other_low, other_high in (
            (0,left,top,bottom),(0,right,top,bottom),
            (1,top,left,right),(1,bottom,left,right)):
        delta = following[:,:,axis]-screen[:,:,axis]
        ratio = (boundary-screen[:,:,axis])/np.where(delta != 0,delta,1)
        other = screen[:,:,1-axis]+ratio*(following[:,:,1-axis]-screen[:,:,1-axis])
        inside = (delta!=0)&(ratio>=0)&(ratio<=1)&(other>=other_low)&(other<=other_high)
        mapped = uv+ratio[:,:,None]*(next_uv-uv)
        low = np.minimum(low,np.min(np.where(inside[:,:,None],mapped,np.inf),axis=1))
        high = np.maximum(high,np.max(np.where(inside[:,:,None],mapped,-np.inf),axis=1))
    for x,y in ((left,top),(left,bottom),(right,top),(right,bottom)):
        a,b,c = _batch_weights(x,y,picker.x[candidates],picker.y[candidates],picker.area[candidates])
        inside = (a>=0)&(b>=0)&(c>=0)
        mapped = a[:,None]*uv[:,0]+b[:,None]*uv[:,1]+c[:,None]*uv[:,2]
        low = np.minimum(low,np.where(inside[:,None],mapped,np.inf))
        high = np.maximum(high,np.where(inside[:,None],mapped,-np.inf))
    valid = np.isfinite(low).all(axis=1)&np.isfinite(high).all(axis=1)
    candidates, low, high = candidates[valid], low[valid], high[valid]
    width,height = size
    boxes = np.column_stack((np.maximum(0,np.floor(low[:,0]*(width-1))),
                             np.maximum(0,np.floor((1-high[:,1])*(height-1))),
                             np.minimum(width-1,np.ceil(high[:,0]*(width-1))),
                             np.minimum(height-1,np.ceil((1-low[:,1])*(height-1))))).astype(np.int64)
    valid = (boxes[:,2]>=boxes[:,0])&(boxes[:,3]>=boxes[:,1])
    return candidates[valid], boxes[valid]


def _masks_batched(picker,candidates,bounds,start,end,size,radius,hardness,paint_through,stencil):
    width,height = size
    uv = picker.uv
    uv_area = picker.uv_area
    front_candidates = candidates
    candidates = candidates[np.abs(uv_area[candidates])>=1e-12]
    candidates, boxes = _clipped_bounds(picker,candidates,bounds,size)
    if not len(candidates):
        return []
    if int(np.sum((boxes[:,2]-boxes[:,0]+1)*(boxes[:,3]-boxes[:,1]+1))) > MAX_WORK_PIXELS:
        raise ValueError('Aproxime o modelo ou reduza o pincel para pintar esta área.')
    front = None if paint_through else _front_batched(picker,front_candidates,bounds)
    stamp = None if stencil is None else np.asarray(stencil.convert('L'),dtype=np.uint8)
    left,top,right,bottom = bounds
    tiles, columns = {}, (width+127)//128
    for ids,x,y in _raster_blocks(candidates,boxes):
        a,b,c = _batch_weights(x/(width-1),1-y/(height-1),uv[ids,:,0],uv[ids,:,1],uv_area[ids])
        px = a*picker.x[ids,0]+b*picker.x[ids,1]+c*picker.x[ids,2]
        py = a*picker.y[ids,0]+b*picker.y[ids,1]+c*picker.y[ids,2]
        alpha = (np.ones_like(px) if stamp is not None else
                 coverage(segment_distance(px,py,start,end),radius,hardness))
        inside = ((a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(px>=left)&(px<=right)
                  &(py>=top)&(py<=bottom)&(alpha>0))
        if front is not None:
            ix = np.clip(np.rint((px-left)*2).astype(np.int32),0,front.shape[1]-1)
            iy = np.clip(np.rint((py-top)*2).astype(np.int32),0,front.shape[0]-1)
            nearest = front[iy,ix]
            front_ids = np.maximum(nearest,0)
            f0,f1,f2 = _batch_weights(px,py,picker.x[front_ids],picker.y[front_ids],
                                    np.where(np.abs(picker.area[front_ids])>1e-12,picker.area[front_ids],1))
            dz = a*picker.depth[ids,0]+b*picker.depth[ids,1]+c*picker.depth[ids,2]
            closest = (f0*picker.depth[front_ids,0]+f1*picker.depth[front_ids,1]+f2*picker.depth[front_ids,2])
            valid_front = (nearest>=0)&(f0>=-1e-6)&(f1>=-1e-6)&(f2>=-1e-6)
            inside &= ~valid_front | (dz>=closest-1e-6)
        if stamp is not None:
            sx,sy = (px-(start[0]-radius))/(radius*2),(py-(start[1]-radius))/(radius*2)
            inside &= (sx>=0)&(sx<=1)&(sy>=0)&(sy<=1)
            stamp_x = np.clip(np.rint(sx*(stamp.shape[1]-1)).astype(np.int32),0,stamp.shape[1]-1)
            stamp_y = np.clip(np.rint(sy*(stamp.shape[0]-1)).astype(np.int32),0,stamp.shape[0]-1)
            alpha = stamp[stamp_y,stamp_x]/255
        x,y,alpha = x[inside],y[inside],np.rint(alpha[inside]*255).astype(np.uint8)
        keys = (y//128)*columns+x//128
        order = np.argsort(keys)
        keys,x,y,alpha = keys[order],x[order],y[order],alpha[order]
        starts = np.flatnonzero(np.r_[True,keys[1:]!=keys[:-1]]) if len(keys) else []
        for begin,finish in zip(starts,np.r_[starts[1:],len(keys)]):
            key = int(keys[begin]); tx,ty = (key % columns)*128,(key//columns)*128
            if key not in tiles:
                tiles[key] = np.zeros((min(128,height-ty),min(128,width-tx)),dtype=np.uint8)
            np.maximum.at(tiles[key],(y[begin:finish]-ty,x[begin:finish]-tx),alpha[begin:finish])
    patches = []
    for key,data in tiles.items():
        image = Image.fromarray(data); box = image.getbbox()
        if box:
            patches.append((image.crop(box),((key % columns)*128+box[0],(key//columns)*128+box[1])))
    return patches


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
    return _masks_batched(picker,candidates,(left,top,right,bottom),start,end,
                          texture_size,radius,hardness,paint_through,stencil)
