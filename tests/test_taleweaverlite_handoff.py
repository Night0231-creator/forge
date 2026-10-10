import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from core.taleweaverlite_handoff import prepare_taleweaverlite_handoff


class TaleWeaverLiteHandoffTests(unittest.TestCase):
    def make_project(self, path):
        path.mkdir()
        objdir=path/'TaleWeaverCmd_Source';objdir.mkdir()
        (objdir/(path.name+'.obj')).write_text(
            'mtllib original.mtl\n'
            'v -2 -0.1 -1\nv 2 0 1\nv 0 1.5 0\n'
            'vt 0 0\nvt 1 0\nvt .5 1\n'
            'vn 0 1 0\nusemtl old\nf 1/1/1 2/2/1 3/3/1\n')
        tw=path/'TaleWeaverLite';tw.mkdir()
        for n in ['Albedo.png','Normal.png','MAES.png']:
            (tw/n).write_bytes(b'\x89PNG\r\n\x1a\n' + b'pixels')
        (tw/'Warrior.fbx').write_bytes(b'fake FBX')

    def test_pack_preserves_uv_normals_and_converts_pivot_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'Warrior'
            self.make_project(root)
            archive, report=prepare_taleweaverlite_handoff(root)
            self.assertEqual(report['requested_talespire_default_scale'],1)
            self.assertEqual(report['suggested_unity_mesh_transform_scale'],8)
            self.assertTrue(report['movement_and_base_not_yet_validated'])
            with ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()),{
                    'Modelo/Model_PivoPes.obj','Modelo/Astronyx_Unity.mtl',
                    'Modelo/Albedo.png','Modelo/Normal.png','Modelo/MAES.png',
                    'Modelo/FBX_Original/Warrior.fbx',
                    'LEIA_PRIMEIRO.txt','CALIBRACAO.json'})
                model=z.read('Modelo/Model_PivoPes.obj').decode()
                self.assertIn('vt 0 0',model)
                self.assertIn('vn 0 1 0',model)
                self.assertIn('mtllib Astronyx_Unity.mtl',model)
                self.assertIn('usemtl AstronyxMini',model)
                self.assertIn('f 1/1/1 2/2/1 3/3/1',model)
                self.assertIn('Default Scale = 1',z.read('LEIA_PRIMEIRO.txt').decode())
            # Never alter original
            self.assertIn('usemtl old',(root/'TaleWeaverCmd_Source/Warrior.obj').read_text())

    def test_invalid_scale_and_missing_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'Warrior';self.make_project(root)
            for bad in [float('nan'),0,-1,13]:
                with self.assertRaises(ValueError):
                    prepare_taleweaverlite_handoff(root,visual_multiplier=bad)
            with self.assertRaises(ValueError):
                prepare_taleweaverlite_handoff(root,default_scale=2)
            with self.assertRaises(FileNotFoundError):
                prepare_taleweaverlite_handoff(Path(tmp)/'Absent')

    def test_missing_png_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'Warrior';self.make_project(root)
            (root/'TaleWeaverLite/Normal.png').unlink()
            with self.assertRaises(FileNotFoundError):
                prepare_taleweaverlite_handoff(root)
