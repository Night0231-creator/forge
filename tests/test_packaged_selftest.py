import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


class PackagedSelfTest(unittest.TestCase):
    def test_source_self_test_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'validate.json'
            result = subprocess.run([sys.executable, str(PROJECT/'studio.py'),
                                     '--self-test', str(report)],
                                    capture_output=True, text=True, cwd=PROJECT,
                                    timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            info = json.loads(report.read_text(encoding='utf-8'))
            self.assertTrue(info['ok'])
            self.assertFalse(info['frozen'])
            self.assertTrue(info['checked']['tcl'])

    def test_source_version(self):
        result = subprocess.run([sys.executable, str(PROJECT/'studio.py'), '--version'],
                                capture_output=True, text=True, cwd=PROJECT, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('2.2.3', result.stdout)
