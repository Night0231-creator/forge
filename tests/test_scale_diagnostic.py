import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from core.scale_diagnostic import build_scale_report, save_scale_diagnostics


class ScaleDiagnosticTests(unittest.TestCase):
    def fixture(self, root, *, prepared_height=1.75, recorded=1.0):
        src = root / 'TaleWeaverCmd_Source'
        stage = root / 'Entrada_TaleWeaverCmd'
        src.mkdir(); stage.mkdir()
        source = 'v 0 0 0\nv 1 0 0\nv 0 1.75 0\nf 1 2 3\n'
        (src / (root.name + '.obj')).write_text(source, encoding='utf-8')
        (stage / 'model.obj').write_text(
            f'v 0 0 0\nv 1 0 0\nv 0 {prepared_height} 0\nf 1 2 3\n',
            encoding='utf-8')
        (root / 'blender_stats.json').write_text(
            json.dumps({'height':1.75,'vertices':3,'requested_height':1.75}))
        (root / 'TaleWeaverCmd_escala.json').write_text(
            json.dumps({'scale_factor':recorded,'effective_height':prepared_height}))
        (stage / 'params.json').write_text(
            json.dumps({'PointsOfInterest':{'Head':{'x':0,'y':1.5,'z':0}}}))
        (root / (root.name + '.tsMod')).write_bytes(b'not-a-real-mod')
        return src,stage

    def test_matching_stages_are_measured(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp) / 'Warrior'; root.mkdir()
            self.fixture(root)
            report=build_scale_report(root)
            self.assertAlmostEqual(report['obj_source']['height'],1.75)
            self.assertAlmostEqual(report['obj_sent_to_taleweavercmd']['height'],1.75)
            self.assertEqual(report['recorded_scale_factor'],1)
            self.assertEqual(report['params_points'],['Head'])
            self.assertTrue(report['tsmod_exists'])
            self.assertFalse(any('não corresponde' in n for n in report['observations']))

    def test_scale_loss_detected_without_blender_guessing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'Warrior';root.mkdir()
            self.fixture(root,prepared_height=.02,recorded=1)
            report=build_scale_report(root)
            self.assertTrue(any('não corresponde' in n for n in report['observations']))
            self.assertTrue(any('menos de metade' in n for n in report['observations']))

    def test_zip_only_generated_artefacts_no_original_blend(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'Warrior';root.mkdir()
            self.fixture(root)
            (root/'Original Meshy.blend').write_bytes(b'private mesh')
            report, archive=save_scale_diagnostics(root)
            self.assertTrue(report.is_file())
            with ZipFile(archive) as z:
                paths=set(z.namelist())
                self.assertIn('Entrada_TaleWeaverCmd/model.obj',paths)
                self.assertIn('TaleWeaverCmd_Source/Warrior.obj',paths)
                self.assertIn('Warrior.tsMod',paths)
                self.assertIn('diagnostico_escala.json',paths)
                self.assertFalse(any(p.endswith('.blend') for p in paths))

    def test_missing_project_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                build_scale_report(temp)


if __name__ == '__main__':
    unittest.main()
