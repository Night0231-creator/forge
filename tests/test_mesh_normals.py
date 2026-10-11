"""Imported normals and smoothing groups must survive the preview loader."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from ui.texture_renderer import load_obj
from ui.gpu_pbr_renderer import _mesh_buffer


class MeshNormalsTests(unittest.TestCase):
    def load(self,faces):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);path=root/'test.obj'
        path.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n'
                        'vt 0 0\nvt 1 0\nvt 0 1\n'+faces)
        Image.new('RGB',(8,8),'white').save(root/'Albedo.png')
        before=path.read_bytes();mesh=load_obj(path)
        self.assertEqual(path.read_bytes(),before)
        return mesh

    def test_positive_negative_corner_normals_are_normalized_and_used_by_gpu(self):
        mesh=self.load('vn 0 3 4\nvn 2 0 0\n'
                       'f 1/1/1 2/2/-1 3/3/1\n')
        np.testing.assert_allclose(mesh.normals[0],[[0,.6,.8],[1,0,0],[0,.6,.8]],atol=1e-6)
        np.testing.assert_allclose(_mesh_buffer(mesh)[:,5:],mesh.normals.reshape(-1,3))

    def test_smoothing_group_joins_normals_at_uv_seams_but_off_keeps_hard_edges(self):
        smooth=self.load('s 1\nf 1/1 2/2 3/3\nf 1/3 4/1 2/2\n')
        expected=np.array([0,1,1])/np.sqrt(2)
        np.testing.assert_allclose(smooth.normals[0,0],expected,atol=1e-6)
        np.testing.assert_allclose(smooth.normals[1,0],expected,atol=1e-6)
        hard=self.load('s off\nf 1/1 2/2 3/3\nf 1/3 4/1 2/2\n')
        np.testing.assert_array_equal(hard.normals[0,0],[0,0,1])
        np.testing.assert_array_equal(hard.normals[1,0],[0,1,0])
        separate=self.load('s 1\nf 1/1 2/2 3/3\ns 2\nf 1/3 4/1 2/2\n')
        np.testing.assert_array_equal(separate.normals,hard.normals)

    def test_bad_or_missing_normals_do_not_drop_geometry_or_reorder_indices(self):
        mesh=self.load('vn nan 0 1\nvn 0 0 0\n'
                       'f 1/1/1 2/2/2 3/3/99\ns on\nf 1/1 4/2 2/3\n')
        self.assertEqual(len(mesh.triangles),2)
        self.assertTrue(np.isfinite(_mesh_buffer(mesh)).all())
        np.testing.assert_array_equal(mesh.triangles,[[0,1,2],[0,3,1]])
        np.testing.assert_array_equal(mesh.normals[0,0],[0,0,1])


if __name__=='__main__':unittest.main()
