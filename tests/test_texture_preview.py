"""Regression tests for OBJ UV/albedo raster preview (no window required)."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from ui.texture_renderer import (load_obj, read_albedo, draw, albedo_for,
                                 PreviewError)


class TexturedPreviewTests(unittest.TestCase):
    def make_model(self, root: Path, with_uv=True):
        obj = root / 'Hero.obj'
        uv = "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n" if with_uv else ""
        faces = ("f 1/1 2/2 3/3\nf 1/1 3/3 4/4\n" if with_uv else
                 "f 1 2 3\nf 1 3 4\n")
        obj.write_text(
            "v -1 -1 0\nv 1 -1 0\nv 1 1 0\nv -1 1 0\n"+uv+faces,
            encoding='utf-8')
        image = np.zeros((64,64,3),dtype=np.uint8)
        image[:,:32] = (255,80,60)
        image[:,32:] = (30,210,90)
        Image.fromarray(image).save(root/'Albedo.png')
        return obj

    def test_obj_uv_face_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            model=self.make_model(Path(folder))
            mesh=load_obj(model)
            self.assertEqual(mesh.triangles.shape,(2,3))
            self.assertEqual(mesh.texcoords.shape,(2,3,2))
            self.assertEqual(albedo_for(model),Path(folder)/'Albedo.png')
            self.assertFalse(mesh.limited)

    def test_textures_are_applied_to_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            mesh=load_obj(self.make_model(Path(folder)))
            texture=read_albedo(mesh.texture_path)
            frame=draw(mesh,texture,0.0,0.0,1.0,240,240)
            pixels=np.asarray(frame)
            non_bg=(pixels!=np.array([17,21,34])).any(axis=2)
            self.assertGreater(int(non_bg.sum()),500)
            colored=pixels[non_bg]
            self.assertTrue((colored[:,0] > colored[:,1]).any())
            self.assertTrue((colored[:,1] > colored[:,0]).any())
            self.assertEqual(frame.size,(240,240))

    def test_missing_uv_raises_preview_only_error(self):
        with tempfile.TemporaryDirectory() as folder:
            obj=self.make_model(Path(folder),with_uv=False)
            with self.assertRaisesRegex(PreviewError,'UV'):
                load_obj(obj)

    def test_negative_obj_indices_and_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            obj=self.make_model(Path(folder))
            lines=obj.read_text()
            obj.write_text(lines+"f -4/1 -3/2 -2/3\n",encoding='utf-8')
            self.assertEqual(load_obj(obj,limit=2).triangles.shape[0],2)
            self.assertTrue(load_obj(obj,limit=2).limited)

    def test_no_albedo_is_visible_error(self):
        with tempfile.TemporaryDirectory() as folder:
            obj=self.make_model(Path(folder))
            (Path(folder)/'Albedo.png').unlink()
            with self.assertRaisesRegex(PreviewError,'Albedo'):
                load_obj(obj)
