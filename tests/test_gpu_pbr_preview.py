"""GPU PBR preview: shader, MAES, orientation, CPU fallback, package checks."""
import tempfile
import unittest
from pathlib import Path
import numpy as np

from ui.gpu_pbr_renderer import (
    VS, FS, _mesh_buffer, _validate_settings, GPUPreview, render_preview,
)
from ui.texture_renderer import load_obj, read_albedo


class GPUPBRTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.obj=root/'Knight.obj'
        self.obj.write_text(
            'v -1 -1 0\nv 1 -1 0\nv 1 1 0\nv -1 1 0\n'
            'vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n'
            'f 1/1 2/2 3/3\nf 1/1 3/3 4/4\n',
            encoding='utf-8'
        )
        from PIL import Image
        Image.new('RGB',(32,32),(180,90,48)).save(root/'Albedo.png')
        self.mesh=load_obj(self.obj)
        self.albedo=read_albedo(self.mesh.texture_path)
        self.maes=np.empty((16,16,4),dtype=np.uint8)
        self.maes[:]=(240,210,0,225)

    def tearDown(self):
        self.temp.cleanup()

    def test_shaders_compile_text_structure_and_mesh_attrs(self):
        self.assertIn('#version 330',VS)
        self.assertIn('uniform sampler2D u_maes;',FS)
        self.assertIn('uniform sampler2D u_normalmap;',FS)
        self.assertIn('float metallic=',FS)
        self.assertIn('float roughness=',FS)
        self.assertIn('vec3 emitted=',FS)
        data=_mesh_buffer(self.mesh)
        self.assertEqual(data.shape,(6,8))
        self.assertTrue(np.isfinite(data).all())
        self.assertAlmostEqual(float(data[0,3]),0.0)

    def test_bad_settings_do_not_break_studio(self):
        for params in [(-1,1),(1,9),(float('nan'),1)]:
            with self.assertRaises(ValueError):
                _validate_settings(*params)

    def test_cpu_fallback_matches_old_viewer_and_does_not_change_textures(self):
        before=self.albedo.tobytes()
        frame,backend=render_preview(
            self.mesh,self.albedo,self.maes,None,0,0,1,180,180,
            force_cpu=True)
        self.assertEqual(frame.size,(180,180))
        self.assertTrue(backend.startswith('CPU'))
        self.assertEqual(before,self.albedo.tobytes())

    def test_optional_open_gl_renders_emissive_and_metal(self):
        # Windows RDP/basic render device may expose OpenGL 1.1 only.
        # Unsupported contexts must still use the CPU path.
        try:
            gpu=GPUPreview()
        except Exception as exc:
            self.skipTest('OpenGL 3.3 indisponível: '+str(exc)[:100])
        try:
            dull=self.maes.copy()
            dull[:]=(0,255,0,10)
            bright=self.maes.copy()
            bright[:]=(0,255,255,10)
            dark=gpu.render(self.mesh,self.albedo,dull,None,0,0,1,180,180,
                            light=0,emission=0)
            lit=gpu.render(self.mesh,self.albedo,bright,None,0,0,1,180,180,
                           light=0,emission=3)
            self.assertEqual(lit.size,(180,180))
            self.assertGreater(np.asarray(lit).mean(),np.asarray(dark).mean())
            self.assertGreaterEqual(gpu.render_calls,2)
        finally:
            try: gpu.ctx.release()
            except Exception: pass


if __name__=='__main__':
    unittest.main()
