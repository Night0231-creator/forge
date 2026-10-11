"""Ensure painting 3D UI and Windows version remain wired."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class SurfacePaintingSourceTests(unittest.TestCase):
    def test_painter_wires_events_and_history(self):
        source=(ROOT/'ui/painting_studio.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("self.viewer.bind('<ButtonPress-1>',self._paint3d_start)",source)
        self.assertIn("self.viewer.bind('<B1-Motion>',self._paint3d_drag)",source)
        self.assertIn('self._worker_projection(camera)',source)
        self.assertIn('self.session.checkpoint()',source)
        self.assertIn('self._schedule_preview()',source)
        self.assertIn('self.viewer.update_paint(self._display_image,',source)

    def test_app_version_consistency(self):
        from core.version import APP_VERSION
        self.assertEqual(APP_VERSION,'5.1.1')
        cli=(ROOT/'studio.py').read_text(encoding='utf-8')
        self.assertIn('Astronyx Mini Forge Studio 5.1.1',cli)


if __name__ == '__main__':
    unittest.main()
