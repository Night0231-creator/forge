import tempfile
import unittest
from pathlib import Path
from core.obj_vertex_budget import (
    inspect_obj_vertex_budget, next_triangle_budget,
    unity_vertex_exception, vertex_error_message, MAX_TALEWEAVER_VERTICES
)


class ObjVertexBudgetTests(unittest.TestCase):
    def test_uv_seams_multiply_imported_vertices(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "hero.obj"
            p.write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
                "vt 0 0\nvt 1 0\nvt 0 1\nvt .1 .1\n"
                "vn 0 0 1\n"
                "usemtl armor\nf 1/1/1 2/2/1 3/3/1\n"
                "f 1/4/1 2/2/1 3/3/1\n", encoding="utf-8")
            report = inspect_obj_vertex_budget(p)
            self.assertEqual(report.positions, 3)
            self.assertEqual(report.split_vertices, 4)
            self.assertEqual(report.faces, 2)
            self.assertEqual(report.face_corners, 6)

    def test_material_splits_also_count(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "hero.obj"
            p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\n"
                         "usemtl A\nf 1 2 3\nusemtl B\nf 1 2 3\n")
            self.assertEqual(inspect_obj_vertex_budget(p).split_vertices, 6)

    def test_budget_decreases_on_importer_overflow(self):
        self.assertLess(next_triangle_budget(100000, 82763), 60000)
        self.assertEqual(next_triangle_budget(100000, 40000), 100000)
        self.assertLess(next_triangle_budget(55000, 65000), 55000)
        with self.assertRaises(ValueError):
            next_triangle_budget(100, 60000)

    def test_exception_parser_prioritizes_vertex_limit_over_gpu_shader_noise(self):
        log = ("ERROR: Shader Sprites/Default shader is not supported on this GPU\n"
               "Caught exception: System.Exception: Creature has 82763 "
               "vertices which exceeds the max allowed count of 60000\n"
               "at Bouncyrock.TaleWeaverCmd")
        self.assertEqual(unity_vertex_exception(log), (82763, 60000))
        self.assertEqual(unity_vertex_exception("ERROR: Shader only"), None)
        self.assertIn("45.000", vertex_error_message(82763))
        self.assertEqual(MAX_TALEWEAVER_VERTICES, 60000)

    def test_invalid_obj_face_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "invalid.obj"
            p.write_text("v 0 0 0\nf 1 2\n")
            with self.assertRaisesRegex(ValueError,"menos"):
                inspect_obj_vertex_budget(p)


if __name__ == "__main__":
    unittest.main()
