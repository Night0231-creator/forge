"""Reusable UV-space volume shadows and edge highlights, prepared off the UI.

This is an artistic geometry/normal/AO treatment, not ray-traced cast shadows.
Maps contain influence, never pigment: later paint receives the same treatment.
CPU-only NumPy batches bound memory and work; no additional viewport passes.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MAX_MAP_SIDE = 1024
MAX_RASTER_PIXELS = 24 * 1024 * 1024


def geometry_signature(project):
    """Invalidate saved maps when the prepared OBJ or its normal map changes."""
    from .footprint_calibrator import find_project_obj
    obj = find_project_obj(Path(project))
    digest = hashlib.sha256()
    paths = [obj]
    for folder in (obj.parent, obj.parent.parent/'TaleWeaverLite',
                   obj.parent.parent/'Entrada_TaleWeaverCmd'):
        normal = next((folder/name for name in ('Normal.png', 'normals.png')
                       if (folder/name).is_file()), None)
        if normal:
            paths.append(normal)
            break
    for path in paths:
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
        digest.update(b'\0')
    return digest.hexdigest()


def _edge_features(points, faces):
    """Signed folds on shared geometric edges; UV seams are not model edges."""
    # Weld exact duplicate positions, common at exported material/UV seams.
    order = np.lexsort((points[:,2],points[:,1],points[:,0]))
    ordered = points[order]
    starts = np.r_[True,np.any(ordered[1:]!=ordered[:-1],axis=1)]
    welded = np.empty(len(points),dtype=np.int32)
    welded[order] = np.cumsum(starts)-1
    points = ordered[starts]
    faces = welded[faces]
    tri = points[faces]
    area = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    lengths = np.linalg.norm(area, axis=1)
    flat = area/np.maximum(lengths[:,None], 1e-12)
    centers = tri.mean(axis=1)
    pairs = faces[:, ((1,2), (2,0), (0,1))].reshape(-1,2)
    pairs.sort(axis=1)
    # Numeric keys avoid NumPy's structured-row comparator retaining the GIL
    # for hundreds of ms on dense meshes; numeric sorting releases it.
    keys = pairs[:,0].astype(np.uint64)*np.uint64(len(points))+pairs[:,1].astype(np.uint64)
    _, inverse, counts = np.unique(keys,return_inverse=True,return_counts=True)
    normals = np.zeros((len(counts),3), dtype=np.float32)
    midpoints = np.zeros_like(normals)
    np.add.at(normals, inverse, np.repeat(flat,3,axis=0))
    np.add.at(midpoints, inverse, np.repeat(centers,3,axis=0))
    other = normals[inverse]-np.repeat(flat,3,axis=0)
    other /= np.maximum(np.linalg.norm(other,axis=1,keepdims=True),1e-12)
    angle = np.sqrt(np.maximum(0,1-(other*np.repeat(flat,3,axis=0)).sum(axis=1)))
    neighbors = (midpoints[inverse]-np.repeat(centers,3,axis=0))/np.maximum(
        counts[inverse,None]-1,1)
    side = ((neighbors-np.repeat(centers,3,axis=0))*np.repeat(flat,3,axis=0)).sum(axis=1)
    folds = -np.sign(side)*np.minimum(angle,1)
    # Boundaries and non-manifold edges have no reliable other surface.
    folds[counts[inverse]!=2] = 0
    edge_lengths = np.linalg.norm(tri[:,(1,2,0)]-tri[:,(2,0,1)],axis=2)
    altitude = lengths[:,None]/np.maximum(edge_lengths,1e-12)
    return flat, folds.reshape(-1,3), altitude


def _atlas_bounds(uv, size):
    w,h = size
    xy = uv*np.array((w-1,-(h-1)),dtype=np.float32)+np.array((0,h-1))
    bounds = np.column_stack((np.clip(np.floor(xy[:,:,0].min(axis=1)),0,w),
                              np.clip(np.floor(xy[:,:,1].min(axis=1)),0,h),
                              np.clip(np.ceil(xy[:,:,0].max(axis=1)),-1,w-1),
                              np.clip(np.ceil(xy[:,:,1].max(axis=1)),-1,h-1))).astype(np.int64)
    return xy, bounds


def build_shading_maps(mesh, texture_size, *, normal_map=None, maes=None):
    """RGB influence atlas: volume/cavity shadow, convex edge, UV coverage.

    Overlapping UVs share a maximum influence; separate treatments require
    separate UV islands. No model geometry or input texture is modified.
    """
    from ui.surface_paint import _raster_blocks, _batch_weights
    w,h = texture_size
    if min(w,h)<2 or w*h>4096*4096:
        raise ValueError('Resolução inválida para o sombreamento.')
    points = np.asarray(mesh.points,dtype=np.float32)
    faces = np.asarray(mesh.triangles,dtype=np.int32)
    uv = np.asarray(mesh.texcoords,dtype=np.float32)
    if (not len(faces) or len(faces)>150000 or uv.shape!=(len(faces),3,2)
            or not np.isfinite(points).all() or not np.isfinite(uv).all()):
        raise ValueError('Malha inválida para o sombreamento automático.')
    if getattr(mesh,'limited',False):
        raise ValueError('Prepare uma malha com até 150 mil faces antes de gerar o sombreamento.')
    area = ((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])
            -(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0]))
    valid = np.abs(area)>1e-12
    if not valid.any():
        raise ValueError('A miniatura precisa de ilhas UV válidas para o sombreamento.')
    flat, folds, altitude = _edge_features(points,faces)
    normals = getattr(mesh,'normals',None)
    if normals is None:
        normals = np.broadcast_to(flat[:,None,:],(len(faces),3,3))
    elif normals.shape!=(len(faces),3,3) or not np.isfinite(normals).all():
        raise ValueError('Normais inválidas para o sombreamento.')
    ratio = min(1,MAX_MAP_SIDE/max(w,h))
    size = (max(2,round(w*ratio)),max(2,round(h*ratio)))
    ids = np.flatnonzero(valid)
    xy,bounds = _atlas_bounds(uv,size)
    visible = (bounds[:,2]>=bounds[:,0])&(bounds[:,3]>=bounds[:,1])
    ids = ids[visible[ids]]
    if not len(ids):
        raise ValueError('Nenhuma ilha UV ocupa a textura da miniatura.')
    def cost():
        boxes = bounds[ids]
        return int(np.sum((boxes[:,2]-boxes[:,0]+1)*(boxes[:,3]-boxes[:,1]+1)))
    # Reduce pathological overlapping atlases before allocating raster batches.
    minimum_side = min(32,min(size))
    while cost()>MAX_RASTER_PIXELS and min(size)>minimum_side:
        ratio = max(minimum_side/min(size),min(.8,(MAX_RASTER_PIXELS/cost())**.5*.9))
        size = tuple(max(2,round(v*ratio)) for v in size)
        xy,bounds = _atlas_bounds(uv,size)
    if cost()>MAX_RASTER_PIXELS:
        raise ValueError('Há muitas ilhas UV sobrepostas. Prepare o mapa UV antes de gerar o efeito.')
    output = np.zeros((size[1]*size[0],3),dtype=np.uint8)
    light = np.array((.35,.77,.53),dtype=np.float32)
    light /= np.linalg.norm(light)
    extent = max(float(np.ptp(points,axis=0).max()),1e-8)
    normal_data = detail = None
    if normal_map is not None:
        image = (normal_map if isinstance(normal_map,Image.Image) else
                 Image.fromarray(np.asarray(normal_map,dtype=np.uint8)))
        image = image.convert('RGB').resize(size,Image.Resampling.BILINEAR)
        normal_data = np.asarray(image,dtype=np.float32)/127.5-1
        smooth = np.asarray(image.filter(ImageFilter.GaussianBlur(1)),dtype=np.float32)/127.5-1
        # Tangent normal divergence estimates small convex/concave details.
        detail = (np.gradient(smooth[:,:,0],axis=1)-np.gradient(smooth[:,:,1],axis=0))*8
    ao = None if maes is None else np.asarray(
        maes.getchannel('G').resize(size,Image.Resampling.BILINEAR),dtype=np.float32)/255
    for face,x,y in _raster_blocks(ids,bounds[ids]):
        a,b,c = _batch_weights(x/(size[0]-1),1-y/(size[1]-1),
                               uv[face,:,0],uv[face,:,1],area[face])
        inside = (a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)
        face,x,y = face[inside],x[inside],y[inside]
        weights = np.column_stack((a[inside],b[inside],c[inside])).astype(np.float32)
        n = (normals[face]*weights[:,:,None]).sum(axis=1)
        n /= np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
        if normal_data is not None:
            tri = points[faces[face]]
            duv1,duv2 = uv[face,1]-uv[face,0],uv[face,2]-uv[face,0]
            tangent = ((tri[:,1]-tri[:,0])*duv2[:,1,None]
                       -(tri[:,2]-tri[:,0])*duv1[:,1,None])/area[face,None]
            tangent -= n*(tangent*n).sum(axis=1,keepdims=True)
            tangent /= np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-12)
            bitangent = np.cross(n,tangent)*np.sign(area[face,None])
            sample = normal_data[y,x]
            mapped = tangent*sample[:,0,None]+bitangent*sample[:,1,None]+n*sample[:,2,None]
            n = mapped/np.maximum(np.linalg.norm(mapped,axis=1,keepdims=True),1e-12)
        distance = np.maximum(weights,0)*altitude[face]
        edge = (np.maximum(folds[face],0)*np.exp(-distance/(extent*.009))).max(axis=1)
        cavity = (np.maximum(-folds[face],0)*np.exp(-distance/(extent*.018))).max(axis=1)
        shadow = .35*(1-np.maximum(n@light,0))+cavity*.65
        if ao is not None:
            shadow = np.maximum(shadow,(1-ao[y,x])*.9)
        if detail is not None:
            shadow += np.maximum(-detail[y,x],0)*.5
            edge += np.maximum(detail[y,x],0)*.65
        index = y*size[0]+x
        np.maximum.at(output[:,0],index,np.rint(np.clip(shadow,0,1)*255).astype('u1'))
        np.maximum.at(output[:,1],index,np.rint(np.clip(edge,0,1)*255).astype('u1'))
        output[index,2] = 255
    output = output.reshape(size[1],size[0],3)
    if not output[:,:,2].any():
        raise ValueError('As ilhas UV são pequenas demais para o mapa de sombreamento.')
    # Extend influences outside islands only; avoid dark texture-filter seams.
    for _ in range(2):
        grown = np.asarray(Image.fromarray(output).filter(ImageFilter.MaxFilter(3)))
        empty = output[:,:,2]==0
        output[empty] = grown[empty]
    return Image.fromarray(output)


@dataclass(frozen=True)
class AutomaticShading:
    maps: Image.Image | None = None
    signature: str = ''
    enabled: bool = False
    shadows: int = 45
    highlights: int = 35

    def configure(self, **changes):
        result = replace(self,**changes)
        if (type(result.enabled) is not bool or any(type(v) is not int or not 0<=v<=100
                                                   for v in (result.shadows,result.highlights))):
            raise ValueError('Sombras e destaques devem ficar entre 0 e 100%.')
        if result.enabled and result.maps is None:
            raise ValueError('Gere o mapa de sombreamento antes de ativar o efeito.')
        if result.maps is not None and (result.maps.mode!='RGB' or
                min(result.maps.size)<2 or max(result.maps.size)>MAX_MAP_SIDE):
            raise ValueError('Mapa de sombreamento inválido.')
        return result

    def apply(self, image, atlas_size, box=None):
        if not self.enabled or not (self.shadows or self.highlights):
            return image
        if box is None:
            box = (0,0,*atlas_size)
        mw,mh = self.maps.size
        aw,ah = atlas_size
        pixels = np.asarray(image).copy()
        for y in range(0,image.height,128):
            bottom = min(y+128,image.height)
            sample = (box[0]*mw/aw,(box[1]+y)*mh/ah,
                      box[2]*mw/aw,(box[1]+bottom)*mh/ah)
            # Globally aligned, bounded row batches also cover non-integral
            # atlas/map scale ratios without a complete float32 4K copy.
            influence = np.asarray(self.maps.resize((image.width,bottom-y),
                Image.Resampling.BILINEAR,box=sample),dtype=np.float32)/255
            rgb = pixels[y:y+128,:,:3].astype(np.float32)
            rgb *= 1-influence[:,:,0,None]*(self.shadows/100)*.75
            rgb += (255-rgb)*influence[:,:,1,None]*(self.highlights/100)*.5
            pixels[y:y+128,:,:3] = np.rint(np.clip(rgb,0,255)).astype('u1')
        return Image.fromarray(pixels)
