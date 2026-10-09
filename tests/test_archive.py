import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from core.archive import extract_meshy_zip


class ArchiveTests(unittest.TestCase):
    def test_extracts_glb_and_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive, dest = Path(tmp) / 'meshy.zip', Path(tmp) / 'out'
            with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
                z.writestr('model/foo.obj', 'v 0 0 0\n')
                z.writestr('model/texture.png', b'PNG')
                z.writestr('model/foo.glb', b'GLB')
            selected = extract_meshy_zip(archive, dest)
            self.assertEqual(selected.name, 'foo.glb')
            self.assertTrue((dest / 'model' / 'texture.png').is_file())

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('../escape.glb', b'wrong')
            with self.assertRaises(ValueError):
                extract_meshy_zip(archive, Path(tmp) / 'out')
            self.assertFalse((Path(tmp) / 'escape.glb').exists())

    def test_rejects_no_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('hello.txt', 'x')
            with self.assertRaises(ValueError):
                extract_meshy_zip(archive, Path(tmp) / 'out')
