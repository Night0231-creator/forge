"""Painting studio tests: real pixels, history, backups and no .tsMod changes."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from core.paint_studio import PaintSession, find_albedo, apply_paint_to_export


class PaintStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'Warrior'
        (self.root / 'TaleWeaverLite').mkdir(parents=True)
        (self.root / 'TaleWeaverCmd_Source').mkdir()
        (self.root / 'Entrada_TaleWeaverCmd').mkdir()
        self.img = self.root / 'TaleWeaverLite' / 'Albedo.png'
        Image.new('RGB', (32,32), '#444444').save(self.img)
        Image.new('RGB', (32,32), '#444444').save(self.root / 'TaleWeaverCmd_Source' / 'Albedo.png')
        Image.new('RGB', (32,32), '#444444').save(self.root / 'Entrada_TaleWeaverCmd' / 'albedo.png')
        self.tsmod = self.root / 'Warrior.tsMod'
        self.tsmod.write_bytes(b'example already generated tsmod unchanged')

    def tearDown(self):
        self.temp.cleanup()

    def test_pencil_undo_redo_and_picker(self):
        session = PaintSession(find_albedo(self.root))
        self.assertEqual(session.pick(10,10), '#444444')
        session.checkpoint()
        session.stroke((10,10),(15,15),'#ff0044',size=5,opacity=1)
        self.assertEqual(session.pick(10,10),'#FF0044')
        self.assertTrue(session.undo())
        self.assertEqual(session.pick(10,10),'#444444')
        self.assertTrue(session.redo())
        self.assertEqual(session.pick(10,10),'#FF0044')
        session.checkpoint()
        session.stroke((10,10),(10,10),'#000000',size=5,erase=True)
        self.assertEqual(session.pick(10,10),'#444444')

    def test_bucket_changes_region(self):
        session=PaintSession(self.img)
        session.checkpoint()
        session.bucket(0,0,'#00aa77')
        self.assertEqual(session.pick(16,16),'#00AA77')
        self.assertTrue(session.undo())
        self.assertEqual(session.pick(16,16),'#444444')

    def test_draft_and_explicit_application_with_backups(self):
        session=PaintSession(self.img)
        session.checkpoint()
        session.stroke((5,5),(5,5),'#ff1199',size=5)
        draft=session.save_draft(self.root)
        self.assertTrue(draft.is_file())
        self.assertEqual(PaintSession(self.img).pick(5,5),'#444444')
        untouched=self.tsmod.read_bytes()
        changed=apply_paint_to_export(self.root,draft)
        self.assertEqual(len(changed),3)
        for image in changed:
            with Image.open(image) as picture:
                self.assertEqual(picture.convert('RGB').getpixel((5,5)),(255,17,153))
            self.assertEqual(len(list(image.parent.glob(image.name+'.*.bak'))),1)
        self.assertEqual(self.tsmod.read_bytes(),untouched)
        self.assertTrue(draft.is_file())

    def test_invalid_nonproject_and_external_draft(self):
        with self.assertRaises(ValueError):
            PaintSession(self.img).save_draft(Path(self.temp.name))
        outside=Path(self.temp.name)/'strange.png'
        Image.new('RGB',(4,4)).save(outside)
        with self.assertRaises(ValueError):
            apply_paint_to_export(self.root,outside)

    def test_large_canvas_guard(self):
        # File size can be tiny but dimensions too large.
        huge=self.root/'large.png'
        Image.new('RGB',(4097,4097)).save(huge)
        with self.assertRaises(ValueError):
            PaintSession(huge)


if __name__ == '__main__':
    unittest.main()
