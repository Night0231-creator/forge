import tempfile
import unittest
from pathlib import Path
from core.library import scan_library


class LibraryTests(unittest.TestCase):
    def test_missing_root(self):
        self.assertEqual(scan_library('/does-not-exist/abc123'), [])

    def test_projects_order_and_completion(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            done = root / 'Dragon'
            done.mkdir()
            (done / 'Dragon.tsMod').write_bytes(b'TSMOD')
            (done / 'Entrada_TaleWeaverCmd').mkdir()
            (done / 'Entrada_TaleWeaverCmd' / 'thumbnail.png').write_bytes(b'thumb')
            work = root / 'Archer'
            work.mkdir()
            (work / 'TaleWeaverCmd_Source').mkdir()
            (work / 'TaleWeaverCmd_Source' / 'Archer.obj').write_text('v 0 0 0')
            (root / 'unrelated').mkdir()
            results = scan_library(root)
            self.assertEqual({p.name for p in results}, {'Dragon', 'Archer'})
            dr = next(p for p in results if p.name == 'Dragon')
            ar = next(p for p in results if p.name == 'Archer')
            self.assertEqual(dr.tsmod.name, 'Dragon.tsMod')
            self.assertIsNotNone(dr.thumbnail)
            self.assertIsNone(ar.tsmod)
            self.assertIsNotNone(ar.obj)

    def test_renamed_tsmod(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            proj = root / 'Wizard'
            proj.mkdir()
            (proj / 'the_wizard.tsMod').write_bytes(b'x')
            self.assertEqual(scan_library(root)[0].tsmod.name, 'the_wizard.tsMod')


if __name__ == '__main__':
    unittest.main()
