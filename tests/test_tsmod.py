"""Unit tests for safe inspect/install helpers (no Blender/TaleSpire needed)."""
import tempfile
import unittest
from pathlib import Path

from core.tsmod import KNOWN_MAGIC, inspect_tsmod, install_tsmod
from core.helpers import validate_config


class TestTsmod(unittest.TestCase):
    def make_mod(self, folder: Path, name: str = 'warlord.tsMod', desc: str = 'warlordexported using Basecoat.') -> Path:
        encoded = desc.encode('utf-16le')
        data = (KNOWN_MAGIC + (1).to_bytes(4, 'little')
                + len(encoded).to_bytes(4, 'little') + (5).to_bytes(4, 'little')
                + bytes(32) + encoded + b'payload-placeholder')
        file = folder / name
        file.write_bytes(data)
        return file

    def test_inspection_real_user_sample(self):
        # Example provided by the user is deliberately NOT shipped with software.
        actual = Path('/mnt/data/eclipse_warlord.tsMod')
        if not actual.exists():
            self.skipTest('Original user .tsMod not present in installed package')
        info = inspect_tsmod(actual)
        self.assertTrue(info['recognized_header'])
        self.assertEqual(info['format_version'], 1)
        self.assertEqual(info['producer'], 'Basecoat')
        self.assertIn('eclipse_warlord', info['description'])

    def test_valid_inspection_and_install_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            input = base / 'input'
            output = base / 'LocalContentPacks'
            input.mkdir()
            output.mkdir()
            src = self.make_mod(input)
            self.assertTrue(inspect_tsmod(src)['recognized_header'])
            dest = install_tsmod(src, output)
            self.assertEqual(dest.read_bytes(), src.read_bytes())
            self.assertEqual(dest, install_tsmod(src, output))
            src.write_bytes(src.read_bytes() + b'NEW')
            with self.assertRaises(FileExistsError):
                install_tsmod(src, output)
            install_tsmod(src, output, replace=True)
            self.assertEqual(dest.read_bytes(), src.read_bytes())
            self.assertTrue(list(output.glob('*.bak')))

    def test_reject_wrong_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = self.make_mod(base)
            with self.assertRaises(ValueError):
                install_tsmod(src, base)

    def test_blend_is_valid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            file = base / 'model.blend'
            file.write_bytes(b'BLENDER-v404')
            settings = validate_config({'source': str(file), 'output_root':str(base / 'dest')})
            self.assertTrue(settings['source'].endswith('.blend'))


if __name__ == '__main__':
    unittest.main()
