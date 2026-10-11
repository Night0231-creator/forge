"""Tests use synthetic geometry and fake Unity folders; never execute Unity."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.unity_bridge import (
    EDITOR_FILE, VALID_EDITOR_VERSION, find_unity_editor,
    find_taleweaverlite_project, import_into_unity_project,
    open_unity_project, validate_unity_project,
)


class UnityBridgeTests(unittest.TestCase):
    def make_unity(self, root):
        (root/'Assets').mkdir(parents=True)
        (root/'Packages').mkdir()
        (root/'ProjectSettings').mkdir()
        (root/'ProjectSettings/ProjectVersion.txt').write_text(
            'm_EditorVersion: 2021.3.45f2\n')
        (root/'Packages/manifest.json').write_text(json.dumps({
            'dependencies': {'com.bouncyrock.taleweaver': 'file:../TaleWeaverPackage'}
        }))
        return root

    def make_mini(self, root):
        root.mkdir()
        folder=root/'TaleWeaverCmd_Source'
        folder.mkdir()
        (folder/(root.name+'.obj')).write_text(
            'mtllib original.mtl\n'
            'v -2 0 -1\nv 2 0 1\nv 0 1.75 0\n'
            'vt 0 0\nvt 1 0\nvt .5 1\n'
            'vn 0 1 0\nusemtl Old\nf 1/1/1 2/2/1 3/3/1\n')
        textures=root/'TaleWeaverLite'
        textures.mkdir()
        for name in ('Albedo.png','Normal.png','MAES.png'):
            (textures/name).write_bytes(b'\x89PNG\r\n\x1a\n' + b'synthetic image')
        return root

    def test_import_stages_assets_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            unity=self.make_unity(home/'AnyNameUnityProject')
            source=self.make_mini(home/'Eclipse Warlord')
            original=(source/'TaleWeaverCmd_Source/Eclipse Warlord.obj').read_bytes()
            first=import_into_unity_project(source,unity)
            target=Path(first['import_path'])
            self.assertTrue(target.is_relative_to(unity.resolve()/'Assets/AstronyxImports'))
            self.assertEqual(first['default_scale'],1)
            self.assertEqual(first['preview_scale'],1.0)
            self.assertIs(first['tsmod_created'],False)
            self.assertTrue((target/'Model_PivoPes.obj').is_file())
            self.assertIn('usemtl AstronyxMini',(target/'Model_PivoPes.obj').read_text())
            self.assertIn('f 1/1/1 2/2/1 3/3/1',(target/'Model_PivoPes.obj').read_text())
            self.assertEqual((target/'Normal.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(original,(source/'TaleWeaverCmd_Source/Eclipse Warlord.obj').read_bytes())
            manifest=json.loads((target/'AstronyxImport.json').read_text(encoding='utf-8'))
            self.assertFalse(manifest['movement_validated_in_game'])
            self.assertEqual(manifest['talespire_default_scale_requested'],1)
            script=(unity/'Assets/Editor'/EDITOR_FILE).read_text(encoding='utf-8')
            self.assertIn('PrefabUtility.SaveAsPrefabAsset',script)
            self.assertIn('Vector3.one',script)
            self.assertNotIn(' -batchmode ',script)
            self.assertIn('MAES',script)
            second=import_into_unity_project(source,unity)
            self.assertNotEqual(first['import_path'],second['import_path'])
            self.assertEqual((unity/'ProjectSettings/ProjectVersion.txt').read_text(),
                             'm_EditorVersion: 2021.3.45f2\n')

    def test_wrong_directory_or_modified_script_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            root=home/'AnotherProject'
            (root/'Assets').mkdir(parents=True)
            (root/'ProjectSettings').mkdir()
            (root/'ProjectSettings/ProjectVersion.txt').write_text(
                'm_EditorVersion: 2021.3.45f2')
            with self.assertRaisesRegex(ValueError,'TaleWeaverLite'):
                validate_unity_project(root)
            unity=self.make_unity(home/'TaleWeaverLite')
            source=self.make_mini(home/'Mini')
            script=unity/'Assets/Editor'/EDITOR_FILE
            script.parent.mkdir()
            script.write_text('// custom code; must not overwrite\n')
            with self.assertRaisesRegex(ValueError,'alterado'):
                import_into_unity_project(source,unity)
            self.assertEqual(script.read_text(),'// custom code; must not overwrite\n')
            self.assertEqual(list((unity/'Assets/AstronyxImports').iterdir()),[])

    def test_editor_detection_and_launch_uses_arguments_not_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            editor=(base/'Unity/Hub/Editor'/VALID_EDITOR_VERSION/'Editor/Unity.exe')
            editor.parent.mkdir(parents=True)
            editor.write_bytes(b'fake executable')
            unity=self.make_unity(base/'TaleWeaverLite')
            with patch.dict(os.environ, {'PROGRAMFILES':str(base),
                                         'ASTRONYX_UNITY_EDITOR':''}, clear=False):
                self.assertEqual(find_unity_editor(),editor.resolve())
                with patch('core.unity_bridge.subprocess.Popen') as proc:
                    open_unity_project(unity)
                    args=proc.call_args.args[0]
                    self.assertEqual(args,[str(editor.resolve()),'-projectPath',str(unity.resolve())])
                    self.assertNotIn('shell',proc.call_args.kwargs)

    def test_project_auto_detection_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            unity=self.make_unity(base/'TaleWeaverLite')
            with patch.dict(os.environ,{'ASTRONYX_TALEWEAVER_PROJECT':str(unity)}):
                self.assertEqual(find_taleweaverlite_project(),unity.resolve())

    def test_rejects_symlinked_asset_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            unity=self.make_unity(home/'TaleWeaverLite')
            assets=unity/'Assets'
            assets.rmdir()
            external=home/'external'
            external.mkdir()
            try:
                assets.symlink_to(external,target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('Symlink creation unavailable')
            with self.assertRaisesRegex(ValueError,'Assets'):
                validate_unity_project(unity)


if __name__ == '__main__':
    unittest.main()
