"""No-display geometry checks; Tk smoke runs separately on Windows."""
import ast
import unittest
from pathlib import Path
from ui.rounded import rounded_points


class RoundedHudTests(unittest.TestCase):
    def test_corner_radius_limits(self):
        p=rounded_points(100,40,10)
        self.assertEqual(p[0],10)
        self.assertIn(100,p)
        self.assertIn(40,p)
        self.assertEqual(len(p),24)
        p2=rounded_points(20,10,100)
        self.assertEqual(p2[0],5)
        with self.assertRaises(ValueError):
            rounded_points(0,20,5)

    def test_studio_and_widget_sources_valid(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('studio.py','app.py','ui/rounded.py','core/update_policy.py'):
            with self.subTest(name=name):
                ast.parse((root/name).read_text(encoding='utf-8'))
