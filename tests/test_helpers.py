"""Dependency-free smoke tests. Run: python -m unittest discover -s tests"""
import tempfile
import unittest
from pathlib import Path

from core.helpers import create_instructions, safe_slug, validate_config, write_manifest


class TestForge(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(safe_slug('Guerreiro: ⚔️ Dragon!'), 'Guerreiro_Dragon')
        self.assertEqual(safe_slug('!!!'), 'Miniatura')

    def test_configuration_valid_and_readable(self):
        with tempfile.TemporaryDirectory() as temp:
            origin = Path(temp) / 'input'
            origin.mkdir()
            input_file = origin / 'dragon.glb'
            input_file.write_bytes(b'glb fake; only helper validation')
            cfg = validate_config({'source': str(input_file), 'output_root': str(Path(temp)/'export'),
                                   'name':'Dragão Azul', 'tris':11000, 'texture_size': 1024,
                                   'height': '1.75', 'rotation': '-90', 'create_plugin': True})
            self.assertEqual(cfg['name'], 'Dragão_Azul')
            output = Path(temp) / 'export' / cfg['name']
            output.mkdir(parents=True)
            stats = {'vertices': 4200, 'triangles': 9800, 'height':1.75}
            create_instructions(output, cfg['name'], stats)
            write_manifest(output, cfg, stats)
            txt = (output / 'LEIA_PRIMEIRO.txt').read_text(encoding='utf-8')
            self.assertIn('LocalContentPacks', txt)
            self.assertIn('.tsMod', txt)
            manifest = (output / 'conversao.json').read_text(encoding='utf-8')
            self.assertNotIn(str(input_file.resolve()), manifest)

    def test_validation_rejects_bad_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'model.glb'
            path.write_bytes(b'not actual 3d')
            cfg = {'source': str(path), 'output_root': temp, 'height': 1.75,
                   'rotation': 0, 'tris': 11000, 'texture_size': 1024}
            for change in ({'texture_size': 3000}, {'tris': 120001}, {'height': -1},
                           {'rotation': 800}):
                with self.assertRaises(ValueError):
                    validate_config({**cfg, **change})


if __name__ == '__main__':
    unittest.main()

class UltraQualityTests(unittest.TestCase):
    def test_4096_textures_accepted(self):
        from core.helpers import validate_config
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'model.glb'
            src.write_bytes(b'fake')
            settings=validate_config({'source':str(src),'output_root':str(Path(folder)/'out'),
                                      'height':1.75,'tris':120000,'texture_size':4096})
            self.assertEqual(settings['texture_size'],4096)
