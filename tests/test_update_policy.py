import unittest

from core.update_policy import AUTO_UPDATE_INTERVAL_MS, STARTUP_DELAY_MS, should_show_update


class UpdatePolicyTests(unittest.TestCase):
    def test_checks_while_open_not_every_second(self):
        self.assertEqual(AUTO_UPDATE_INTERVAL_MS, 300000)
        self.assertGreaterEqual(STARTUP_DELAY_MS, 500)

    def test_same_release_is_not_notified_repeatedly(self):
        self.assertTrue(should_show_update('2.2.8', None))
        self.assertFalse(should_show_update('2.2.8', '2.2.8'))
        self.assertTrue(should_show_update('2.2.9', '2.2.8'))
        self.assertTrue(should_show_update('2.2.8', '2.2.8', manual=True))

    def test_invalid_version_rejected(self):
        with self.assertRaises(ValueError):
            should_show_update('bad', None)
