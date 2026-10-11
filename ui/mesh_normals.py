"""Prepare per-corner OBJ normals once, retaining sharp edges and UV seams."""
import numpy as np


def corner_normals(points, faces, supplied, groups):
    points=np.asarray(points,dtype=np.float32)
    faces=np.asarray(faces,dtype=np.int32)
    tri=points[faces]
    area=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    flat=area/np.maximum(np.linalg.norm(area,axis=1,keepdims=True),1e-12)
    result=np.broadcast_to(flat[:,None,:],tri.shape).copy()
    groups=np.asarray(groups,dtype=np.int32)
    smooth=groups>0
    if smooth.any():
        ids=faces[smooth].reshape(-1)
        keys=np.column_stack((ids,np.repeat(groups[smooth],3)))
        _,inverse=np.unique(keys,axis=0,return_inverse=True)
        summed=np.zeros((int(inverse.max())+1,3),dtype=np.float32)
        np.add.at(summed,inverse,np.repeat(area[smooth],3,axis=0))
        lengths=np.linalg.norm(summed,axis=1,keepdims=True)
        averaged=summed/np.maximum(lengths,1e-12)
        calculated=averaged[inverse].reshape(-1,3,3)
        valid=np.linalg.norm(calculated,axis=2)>1e-8
        result[smooth]=np.where(valid[:,:,None],calculated,result[smooth])
    imported=np.asarray(supplied,dtype=np.float32)
    lengths=np.linalg.norm(imported,axis=2)
    valid=np.isfinite(imported).all(axis=2)&(lengths>1e-8)
    result[valid]=imported[valid]/lengths[valid,None]
    return np.ascontiguousarray(result,dtype=np.float32)
