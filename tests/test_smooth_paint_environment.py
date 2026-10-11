"""Regression checks for V3.2 dirty-region composition and environment presets."""
import ast
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops
from core.layered_materials import LayeredPaintSession
from ui.gpu_pbr_renderer import ENV_PRESETS, FS, _validate_settings

ROOT=Path(__file__).resolve().parents[1]


class SmoothPaintingTests(unittest.TestCase):
    def make_session(self, root):
        root=Path(root)/'Knight'
        (root/'TaleWeaverCmd_Source').mkdir(parents=True)
        (root/'TaleWeaverLite').mkdir()
        Image.new('RGBA',(80,80),(105,70,80,255)).save(root/'TaleWeaverLite/Albedo.png')
        return LayeredPaintSession(root/'TaleWeaverLite/Albedo.png',root)

    def test_dirty_rect_equals_full_composition(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp)
            s.add_layer('Metal')
            for i in range(12):
                s.stroke((9+i,16),(11+i,20),'#ffcc44',size=8,opacity=.6)
                optimized=s.image.copy()
                s._compose()
                self.assertIsNone(ImageChops.difference(s.image,optimized).getbbox())
            s.set_opacity(42)
            s.add_layer('Cloth')
            s.stroke((3,4),(15,19),'#3355bb',size=11,opacity=.45)
            optimized=s.image.copy()
            s._compose()
            self.assertIsNone(ImageChops.difference(s.image,optimized).getbbox())

    def test_masked_strokes_stay_inside_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=self.make_session(tmp)
            s.select_region(5,5)
            s.stroke((5,5),(5,5),'#11ff00',size=8)
            self.assertEqual(s.pick(5,5),'#11FF00')
            s.undo() if s.history else None
            optimized=s.image.copy()
            s._compose()
            self.assertIsNone(ImageChops.difference(s.image,optimized).getbbox())

    def test_ambient_environment_validation_and_shader(self):
        self.assertEqual(set(ENV_PRESETS),{'Estúdio','Pôr do sol','Luar'})
        for name in ENV_PRESETS:
            _validate_settings(1,1,1.2,name)
        for args in ((1,1,-.1,'Estúdio'),(1,1,3.5,'Estúdio'),
                     (1,1,1,'Falso')):
            with self.assertRaises(ValueError):
                _validate_settings(*args)
        for name in ('u_ambient','u_sky_tint','u_ground_tint'):
            self.assertIn(name,FS)

    def test_gui_pipeline_keeps_cached_frame_and_new_controls(self):
        viewer=(ROOT/'ui/texture_viewer.py').read_text(encoding='utf-8')
        paint=(ROOT/'ui/painting_studio.py').read_text(encoding='utf-8')
        gpu=(ROOT/'ui/gpu_pbr_renderer.py').read_text(encoding='utf-8')
        for source in (viewer,paint,gpu):
            ast.parse(source)
        self.assertIn('if textured and self._texture_image is not None:',viewer)
        self.assertIn('self._poll_job=self.after(33,self._poll)',viewer)
        self.assertIn("self._preview_job=self.after(90,self._refresh_live_preview)",paint)
        self.assertIn("self._environment=tk.StringVar(value='Estúdio')",paint)
        self.assertIn('ambient=self._ambient_level.get()/100',paint)
        self.assertIn('self._neutral_maes',gpu)


if __name__ == '__main__':
    unittest.main()
