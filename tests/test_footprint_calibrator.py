"""Regression tests: geometry != TaleSpire physical collider or gameplay size."""
import json
import tempfile
import unittest
from pathlib import Path

from core.footprint_calibrator import (
    analyze_footprint, find_project_obj, write_calibration_report,
)


class FootprintCalibratorTests(unittest.TestCase):
    def write_obj(self, path, coordinates):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(
            ''.join(f'v {x} {y} {z}\n' for x,y,z in coordinates)
            + 'f 1 2 3\n',encoding='utf-8')
        return path

    def character(self, factor=1):
        points=[]
        for i in range(60):
            y=1.75*i/59
            # narrow body; feet are at +/- 0.1
            for x in (-.18,.18):
                for z in (-.14,.14):
                    points.append((x*factor,y*factor,z*factor))
        return points

    def test_normal_mesh_has_geometric_reference_not_gameplay_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            source=self.write_obj(Path(temp)/'warrior.obj', self.character())
            report=analyze_footprint(source)
            self.assertAlmostEqual(report.report.height,1.75,places=4)
            self.assertAlmostEqual(report.report.width,.36,places=4)
            self.assertEqual(report.report.footprint_reference,1)
            self.assertEqual(report.report.humanoid_height_reference,1.75)
            self.assertLess(report.report.offset_from_center,.01)
            self.assertIsNotNone(report.report.core_width)
            self.assertLessEqual(len(report.points),2400)
            data=report.report.to_dict()
            self.assertIs(data['visual_references']['physical_collision_verified'],False)
            self.assertIs(data['visual_references']['default_scale_verified'],False)
            self.assertIn('NÃO confirma',data['observations'][0])
            self.assertIn('somente um teste no jogo',data['caveat'])

    def test_eight_times_character_is_flagged_not_rescaled(self):
        with tempfile.TemporaryDirectory() as temp:
            obj=self.write_obj(Path(temp)/'giant.obj',self.character(8))
            original=obj.read_bytes()
            report=analyze_footprint(obj).report
            self.assertAlmostEqual(report.height,14,places=4)
            self.assertTrue(any('altura' in x.casefold() for x in report.observations))
            self.assertTrue(any('2 unidades' in x for x in report.observations))
            self.assertEqual(obj.read_bytes(),original)

    def test_wide_accessory_is_not_interpreted_as_true_base(self):
        with tempfile.TemporaryDirectory() as temp:
            points=self.character()+[(-7,1.2,0),(7,1.2,0)]
            obj=self.write_obj(Path(temp)/'sword.obj',points)
            report=analyze_footprint(obj).report
            self.assertAlmostEqual(report.width,14)
            self.assertLess(report.core_width,1)
            self.assertTrue(any('acessórios' in x for x in report.observations))
            self.assertIn('não',report.caveat.lower())

    def test_shifted_feet_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            points=self.character()
            # High vertices concentrated far from footprint.
            points += [(2.5,1.2,0),(2.9,1.2,0)]
            obj=self.write_obj(Path(temp)/'shifted.obj',points)
            report=analyze_footprint(obj).report
            self.assertTrue(any('deslocado' in x for x in report.observations))
            self.assertGreater(report.offset_from_center,.20)

    def test_report_uses_final_cmd_obj_and_never_modifies_it(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)/'Eclipse'
            staged=self.write_obj(project/'Entrada_TaleWeaverCmd/model.obj',
                                  self.character(factor=1))
            self.write_obj(project/'TaleWeaverCmd_Source/Eclipse.obj',
                           self.character(factor=8))
            before=staged.read_bytes()
            self.assertEqual(find_project_obj(project),staged)
            saved=write_calibration_report(project)
            data=json.loads(saved.read_text(encoding='utf-8'))
            self.assertAlmostEqual(data['bounds']['height'],1.75,places=4)
            self.assertEqual(staged.read_bytes(),before)
            self.assertEqual(saved.name,'calibracao_visual_1x1.json')

    def test_missing_final_uses_source_and_outside_project_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'Hero'
            source=self.write_obj(root/'TaleWeaverCmd_Source/hero.obj',
                                  self.character())
            self.assertEqual(find_project_obj(root),source)
            self.assertTrue(write_calibration_report(root).is_file())
            outside=self.write_obj(Path(temp)/'outside.obj',self.character())
            with self.assertRaises(ValueError):
                write_calibration_report(root,outside)

    def test_bad_or_flat_mesh_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            obj=self.write_obj(Path(temp)/'flat.obj',
                               [(0,0,0),(1,0,0),(2,0,0)])
            with self.assertRaises(ValueError):
                analyze_footprint(obj)
            with self.assertRaises(ValueError):
                analyze_footprint(obj,reference_height=100)
