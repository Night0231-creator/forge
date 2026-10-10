"""Smoke test for the V2.2 Tk layout on the Windows Actions runner.

This test never invokes Blender, TaleWeaverCmd, game assets or the updater.
"""
import sys
import unittest
from unittest.mock import patch

@unittest.skipUnless(sys.platform == 'win32', 'Requires Windows desktop Tk')
class StudioHudSmoke(unittest.TestCase):
    def test_dashboard_studio_library_and_navigation(self):
        from studio import Studio
        with patch.object(Studio, '_begin_updates', return_value=None):
            app=Studio()
        try:
            app.withdraw()
            self.assertIsNotNone(app.tab_dashboard)
            self.assertIsNotNone(app.tab_preview)
            from ui.rounded import RoundedNavButton, RoundedEntry, RoundedSelect
            self.assertIsInstance(app.nav_buttons['home'], RoundedNavButton)
            self.assertTrue(app.auto_update_check.get())
            self.assertIn('studio', app.nav_buttons)

            self.assertTrue(app.hud_stats)
            app._navigate('studio', 'tab_preview')
            self.assertEqual(app.tabs.select(), str(app.tab_preview))
            app._navigate('library', 'tab_library')
            self.assertEqual(app.tabs.select(), str(app.tab_library))
            app.library_search.set('Eclipse')
            app.library_filter.set('Prontos')
            app.update_idletasks()
        finally:
            app.destroy()
