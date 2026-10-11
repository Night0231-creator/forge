"""V4 single-desk workbench and high-poly colored fallback tests."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from core.layered_materials import LayeredPaintSession
from ui.texture_renderer import TextureMesh, draw_fast
from ui.gpu_pbr_renderer import render_preview

ROOT=Path(__file__).resolve().parents[1]


class FullStudioTests(unittest.TestCase):
    def test_full_color_fallback_renders_dense_faces(self):
        points=np.array([[-1.,-1.,0.],[1.,-1.,0.],
                         [1.,1.,0.],[-1.,1.,0.]],dtype=np.float32)
        triangles=np.array([(0,1,2),(0,2,3)]*2400,dtype=np.int32)
        texcoords=np.array([[(0,0),(1,0),(1,1)],
                            [(0,0),(1,1),(0,1)]]*2400,dtype=np.float32)
        mesh=TextureMesh(points,triangles,texcoords,Path('Albedo.png'))
        albedo=np.zeros((32,32,3),dtype=np.uint8)
        albedo[:]=(220,104,68)
        frame=draw_fast(mesh,albedo,0,0,1,180,180)
        arr=np.asarray(frame)
        self.assertGreater(int(arr[90,90,0]),110)
        self.assertGreater(int(arr[90,90,0]),int(arr[90,90,2]))
        before=albedo.copy()
        result,backend=render_preview(
            mesh,albedo,None,None,0,0,1,180,180,force_cpu=True)
        self.assertTrue(backend.startswith('CPU · Albedo'))
        self.assertEqual(result.size,(180,180))
        np.testing.assert_array_equal(before,albedo)

    def test_stamps_integrate_with_layers_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)
            (project/'TaleWeaverLite').mkdir()
            source=project/'TaleWeaverLite/Albedo.png'
            Image.new('RGBA',(96,96),'#606060').save(source)
            session=LayeredPaintSession(source,project)
            session.checkpoint()
            session.stamp(45,45,'#00EEFF',diameter=32,shape='Estrela')
            self.assertNotEqual(session.pick(45,32),'#606060')
            self.assertTrue(session.undo())
            self.assertEqual(session.pick(45,32),'#606060')
            custom=Image.new('RGBA',(16,16),(0,0,0,0))
            from PIL import ImageDraw
            ImageDraw.Draw(custom).ellipse((1,1,14,14),fill=(255,255,255,255))
            session.checkpoint()
            session.stamp(45,45,'#FF5500',diameter=32,custom=custom)
            self.assertEqual(session.pick(45,45),'#FF5500')
            with self.assertRaises(ValueError):
                session.stamp(45,45,'#FF5500',diameter=2)

    def test_studio_replaces_dark_preview_home(self):
        sources={key:(ROOT/key).read_text(encoding='utf-8') for key in
                 ('ui/studio_workspace.py','studio.py','ui/painting_studio.py',
                  'ui/gpu_pbr_renderer.py')}
        for s in sources.values(): ast.parse(s)
        workspace=sources['ui/studio_workspace.py']
        self.assertIn('self._select_project(target,first=True)',workspace)
        self.assertIn('on_exit=self._back_to_library',workspace)
        self.assertIn('editor=PaintingStudio(self.editor_frame,item.folder',workspace)
        self.assertNotIn('self.preview=TexturedObjViewer',workspace)
        self.assertIn('self.hero_bar.pack_forget()',sources['studio.py'])
        self.assertIn('self.status_bar.pack_forget()',sources['studio.py'])
        self.assertIn('draw_fast(mesh,albedo',sources['ui/gpu_pbr_renderer.py'])
        self.assertIn("('Carimbo','carimbo')",sources['ui/painting_studio.py'])


if __name__=='__main__':
    unittest.main()
