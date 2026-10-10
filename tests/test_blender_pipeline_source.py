import ast
import unittest
from pathlib import Path

class BlenderPipelineSourceTests(unittest.TestCase):
    def test_syntax_and_modern_smoothing(self):
        code=(Path(__file__).resolve().parents[1]/'core/blender_pipeline.py').read_text(encoding='utf8')
        ast.parse(code)
        self.assertNotIn('obj.data.use_auto_smooth',code)
        self.assertIn('bmesh.ops.recalc_face_normals',code)
        self.assertIn("stats['footprint_scale_applied']",code)

    def test_meshy_png_and_atlas_fidelity_path_is_present(self):
        code=(Path(__file__).resolve().parents[1]/'core/blender_pipeline.py').read_text(encoding='utf8')
        ast.parse(code)
        self.assertIn("def try_preserve_png_albedo(",code)
        self.assertIn("image.packed_file",code)
        self.assertIn("stats['albedo_method']",code)
        self.assertIn("triangle_retention_percent",code)
        self.assertIn("bpy.ops.uv.smart_project(island_margin=0.008)",code)
        self.assertIn("render_thumbnail(obj, cmd_dir / 'thumbnail.png', stats['height'])",code)

    def test_post_export_vertex_budget_is_checked_and_corrected(self):
        code=(Path(__file__).resolve().parents[1]/'core/blender_pipeline.py').read_text(encoding='utf8')
        ast.parse(code)
        self.assertIn('def enforce_taleweaver_vertex_budget(',code)
        self.assertIn('inspect_obj_vertex_budget(cmd_dir',code)
        self.assertIn('next_triangle_budget(faces, budget.split_vertices)',code)
        self.assertIn("stats['taleweavercmd_obj_split_vertices']",code)
        self.assertIn('export_fbx(obj, tw, cfg[\'name\'])',code)
