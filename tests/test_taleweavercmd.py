"""Unit tests for the official TaleWeaverCmd README contract.

They simulate process output; real TaleWeaverCmd must be run on user's Windows PC.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.taleweavercmd import (
    build_params, default_points, ensure_cmd_files, prepare_cmd_input,
    run_taleweavercmd, REQUIRED_FILES,
)


def create_source(base: Path, name='Guerreiro') -> Path:
    folder = base / name
    stage = folder / 'TaleWeaverCmd_Source'
    stage.mkdir(parents=True)
    for src in (f'{name}.obj', 'Albedo.png', 'Normal.png', 'MAES.png', 'thumbnail.png'):
        (stage / src).write_bytes(b'test fixture')
    return folder


class FakeProcess:
    def __init__(self, returncode=0):
        self.stdout = io.StringIO('TaleWeaverCmd test result\n')
        self._code = returncode
    def wait(self):
        return self._code


class TestOfficialCmd(unittest.TestCase):
    def test_staging_uses_exact_six_official_filenames(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            stage = prepare_cmd_input(folder, 'Guerreiro', 1.8)
            self.assertEqual(set(REQUIRED_FILES), {p.name for p in stage.iterdir()})
            self.assertEqual((stage/'model.obj').read_bytes(), b'test fixture')
            ensure_cmd_files(stage)
            data = json.loads((stage/'params.json').read_text(encoding='utf-8'))
            self.assertEqual(data['Name'], 'Guerreiro')
            self.assertEqual(data['TsTags'], [])
            self.assertIs(data['UsePaint'], True)
            self.assertEqual(list(data['PointsOfInterest']), ['Head', 'Spell', 'Hit', 'Torch'])
            self.assertAlmostEqual(data['PointsOfInterest']['Head']['y'], 1.602)

    def test_reexport_preserves_custom_points(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            stage = prepare_cmd_input(folder, 'Guerreiro')
            data = json.loads((stage/'params.json').read_text(encoding='utf-8'))
            data['PointsOfInterest']['Head']['y'] = 9.9
            (stage/'params.json').write_text(json.dumps(data))
            prepare_cmd_input(folder, 'Guerreiro', 1.75, preserve_params=True)
            persisted = json.loads((stage/'params.json').read_text(encoding='utf-8'))
            self.assertEqual(persisted['PointsOfInterest']['Head']['y'], 9.9)

    def test_missing_required_thumbnail_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            (folder/'TaleWeaverCmd_Source'/'thumbnail.png').unlink()
            with self.assertRaisesRegex(FileNotFoundError, 'thumbnail.png'):
                prepare_cmd_input(folder, 'Guerreiro')

    def test_points_scale_with_height(self):
        self.assertGreater(default_points(2)['Head']['y'], default_points(1)['Head']['y'])
        with self.assertRaises(ValueError):
            build_params('Mini', -1)

    def test_command_calls_srcdir_and_returns_created_tsmod(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            exe = Path(d)/'TaleWeaverCmd.exe'
            exe.write_text('stub')
            def process_factory(args, **_):
                self.assertEqual(Path(args[0]).resolve(), exe.resolve())
                self.assertEqual(args[1], '-srcDir')
                self.assertEqual(args[3], '-logFile')
                stage = Path(args[2])
                self.assertTrue((stage/'params.json').is_file())
                (stage/'converted.tsMod').write_bytes(b'\xce\xd1\xce\xd1' + b'fake-data'*20)
                return FakeProcess()
            with patch('core.taleweavercmd.subprocess.Popen', side_effect=process_factory):
                result = run_taleweavercmd(exe, folder, 'Guerreiro')
            self.assertEqual(result.resolve(), (folder/'Guerreiro.tsMod').resolve())
            self.assertTrue(result.is_file())

    def test_does_not_accept_stale_or_missing_output(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            exe = Path(d)/'TaleWeaverCmd.exe'
            exe.write_text('stub')
            stage = folder/'Entrada_TaleWeaverCmd'
            stage.mkdir()
            (stage/'converted.tsMod').write_bytes(b'PREVIOUS OUTPUT'*200)
            with patch('core.taleweavercmd.subprocess.Popen', return_value=FakeProcess()):
                with self.assertRaisesRegex(RuntimeError, 'sem criar converted.tsMod'):
                    run_taleweavercmd(exe, folder, 'Guerreiro')
            self.assertFalse((stage/'converted.tsMod').exists())

    def test_nonzero_exit_is_error(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            exe = Path(d)/'TaleWeaverCmd.exe'
            exe.write_text('stub')
            with patch('core.taleweavercmd.subprocess.Popen', return_value=FakeProcess(1)):
                with self.assertRaisesRegex(RuntimeError, 'código 1'):
                    run_taleweavercmd(exe, folder, 'Guerreiro')

    def test_previous_final_is_backed_up(self):
        with tempfile.TemporaryDirectory() as d:
            folder = create_source(Path(d))
            exe = Path(d)/'TaleWeaverCmd.exe'
            exe.write_text('stub')
            final = folder/'Guerreiro.tsMod'
            final.write_bytes(b'Old')
            def fake_process(args, **_):
                (Path(args[2])/'converted.tsMod').write_bytes(b'New'*50)
                return FakeProcess()
            with patch('core.taleweavercmd.subprocess.Popen', side_effect=fake_process):
                run_taleweavercmd(exe, folder, 'Guerreiro')
            self.assertEqual(final.read_bytes(), b'New'*50)
            self.assertEqual(len(list(folder.glob('Guerreiro.tsMod.*.bak'))), 1)


if __name__ == '__main__':
    unittest.main()


class TaleWeaverDiagnosticsTests(unittest.TestCase):
    def test_log_filters_unity_memorysetup_noise(self):
        from core.taleweavercmd import _read_log_errors
        with tempfile.TemporaryDirectory() as folder:
            logfile = Path(folder) / 'taleweavercmd.log'
            logfile.write_text(
                '-memorysetup-job-temp-allocator-block-size=2097152\n'
                'Initialize engine version: 2022\n'
                'Error: unable to load albedo.png\n',
                encoding='utf-8')
            result = _read_log_errors(logfile, ['-memorysetup-temp-allocator-size=262144'])
            self.assertIn('unable to load albedo', result)
            self.assertNotIn('memorysetup-', result)

    def test_large_png_is_downscaled_only_in_staging(self):
        from core.taleweavercmd import _copy_compatible_texture
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'Albedo.png'
            dest = Path(folder) / 'staged_albedo.png'
            Image.new('RGB', (2300, 1200), (125, 140, 210)).save(source)
            _copy_compatible_texture(source, dest)
            with Image.open(source) as orig, Image.open(dest) as result:
                self.assertEqual(orig.size, (2300, 1200))
                self.assertLessEqual(max(result.size), 2048)

    def test_missing_runtime_dependencies_give_actionable_error(self):
        import os
        from core.taleweavercmd import _verify_tool_runtime
        if os.name != 'nt':
            self.skipTest('Unity runtime validation is Windows-specific')
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'TaleWeaverCmd.exe'
            exe.write_bytes(b'MZ' + b'\\0' * 20)
            with self.assertRaisesRegex(RuntimeError, 'UnityPlayer.dll'):
                _verify_tool_runtime(exe)
            (Path(folder) / 'UnityPlayer.dll').write_bytes(b'test')
            (Path(folder) / 'TaleWeaverCmd_Data').mkdir()
            _verify_tool_runtime(exe)
