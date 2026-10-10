"""Visual comparison must use a single world-unit scale and stay read-only."""
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from ui.size_reference import paint_reference, project_reference_y
from ui.texture_renderer import draw, load_obj, read_albedo


class SizeReferenceTests(unittest.TestCase):
    def test_projection_shares_world_units(self):
        a = project_reference_y(0, base_y=0, center_y=.875,
                                pixels_per_unit=100, pitch=0,
                                frame_height=300, reference_height=1.75)
        b = project_reference_y(1, base_y=0, center_y=.875,
                                pixels_per_unit=100, pitch=0,
                                frame_height=300, reference_height=1.75)
        self.assertAlmostEqual(a-b, 175.0)
        tilted = project_reference_y(1, base_y=0, center_y=.875,
                                     pixels_per_unit=100, pitch=math.pi/2,
                                     frame_height=300, reference_height=1.75)
        foot = project_reference_y(0, base_y=0, center_y=.875,
                                   pixels_per_unit=100, pitch=math.pi/2,
                                   frame_height=300, reference_height=1.75)
        self.assertAlmostEqual(tilted, foot, places=5)

    def test_silhouette_changes_only_frame(self):
        image = Image.new('RGB',(360,300),(17,21,34))
        result = paint_reference(image.copy(), base_y=0, center_y=.8,
                                 model_height=1.6, pixels_per_unit=100,pitch=0)
        self.assertEqual(result.size,image.size)
        self.assertGreater(np.count_nonzero(np.any(
            np.asarray(result)!=np.asarray(image), axis=2)), 50)
        self.assertEqual(image.getpixel((40,40)), (17,21,34))
        with self.assertRaises(ValueError):
            paint_reference(image,base_y=0,center_y=0,model_height=0,
                            pixels_per_unit=float('nan'),pitch=0)

    def test_render_reference_with_uv_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            obj = root/'Hero.obj'
            obj.write_text('v -0.2 0 0\nv 0.2 0 0\nv 0 1.75 0\n'
                           'vt 0 0\nvt 1 0\nvt 0.5 1\n'
                           'f 1/1 2/2 3/3\n',encoding='utf-8')
            Image.new('RGB',(16,16),(120,160,210)).save(root/'Albedo.png')
            mesh = load_obj(obj)
            tex = read_albedo(mesh.texture_path)
            plain = draw(mesh,tex,0,0,1,360,300)
            compare = draw(mesh,tex,0,0,1,360,300,show_reference=True)
            self.assertEqual(compare.size,plain.size)
            self.assertFalse(np.array_equal(np.asarray(plain),np.asarray(compare)))
