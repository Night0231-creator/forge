"""Unit tests for safe inspect/install helpers (no Blender/TaleSpire needed)."""
import tempfile
import unittest
from pathlib import Path

from core.tsmod import (KNOWN_MAGIC, inspect_tsmod, install_tsmod,
                        compare_tsmod_reference, format_tsmod_reference_report)
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

    def test_known_basecoat_reference_compared_with_taleweaver_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            base=self.make_mod(root, 'eclipse_warlord_reference.tsMod',
                'eclipse_warlordexported using Basecoat.')
            newer=self.make_mod(root, 'new_eclipse.tsMod',
                'Created by another tool')
            info=inspect_tsmod(base)
            self.assertEqual(info['header_magic'], 'ced1ced1')
            self.assertEqual(info['format_version'], 1)
            self.assertEqual(info['header_aux'], 5)
            self.assertEqual(info['producer'], 'Basecoat')
            report=compare_tsmod_reference(base,newer)
            self.assertEqual(report['status'],'cabecalho_compatível')
            self.assertTrue(report['same_magic'])
            self.assertTrue(report['same_format_version'])
            self.assertEqual(report['reference']['producer'], 'Basecoat')
            self.assertNotEqual(report['candidate']['producer'], 'Basecoat')
            self.assertFalse(report['same_file'])
            self.assertIn('NÃO confirma',format_tsmod_reference_report(report))

    def test_copy_of_reference_is_identical_without_copying_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            base=self.make_mod(root)
            copy=root/'copy.tsMod'
            copy.write_bytes(base.read_bytes())
            report=compare_tsmod_reference(base,copy)
            self.assertEqual(report['status'],'arquivo_identico')
            self.assertIn('cópia idêntica',format_tsmod_reference_report(report))

    def test_invalid_reference_rejected_and_different_version_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            base=self.make_mod(root)
            incompatible=self.make_mod(root,'other.tsMod')
            data=bytearray(incompatible.read_bytes())
            data[4:8]=(2).to_bytes(4,'little')
            incompatible.write_bytes(data)
            self.assertEqual(compare_tsmod_reference(base,incompatible)['status'],
                             'versao_diferente')
            bad=root/'unknown.tsMod'
            bad.write_bytes(b'bad!'*20)
            with self.assertRaisesRegex(ValueError,'referência'):
                compare_tsmod_reference(bad,base)
            self.assertEqual(compare_tsmod_reference(base,bad)['status'],
                             'cabecalho_diferente')

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
