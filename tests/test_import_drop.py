import tempfile
import unittest
from pathlib import Path
from core.import_drop import parse_dropped_model, display_model_name


class ImportDropTests(unittest.TestCase):
    def test_accepts_glb_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'Eclipse Warlord.glb'
            file.write_bytes(b'placeholder')
            got = parse_dropped_model('{' + str(file) + '}', lambda value: [value[1:-1]])
            self.assertEqual(got, file.resolve())
            self.assertEqual(display_model_name(got), 'Eclipse_Warlord')

    def test_accepts_meshy_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'My Model.ZIP'
            file.write_bytes(b'placeholder')
            self.assertEqual(parse_dropped_model(str(file), lambda value:[value]), file.resolve())

    def test_rejects_multiple_missing_or_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'installer.exe'
            bad.write_bytes(b'placeholder')
            for entry, names in (
                ('two files', ['model.glb', 'model2.glb']),
                (str(bad), [str(bad)]),
                (str(Path(directory)/'not-found.glb'), [str(Path(directory)/'not-found.glb')])):
                with self.subTest(entry=entry), self.assertRaises(ValueError):
                    parse_dropped_model(entry,lambda _text,names=names:names)
