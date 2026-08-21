#!/usr/bin/env python3
"""Tests for CLI, version sync, and daily-fetch date handling.

Enforces:
- CLI --version/--help surface the real package version
- CLI exits non-zero on bad input and writes errors to stderr
- api.py VERSION is synced to pyproject.toml version (no hardcoded drift)
- daily-astrology-fetch uses Tehran-local time, not UTC floor
"""
import json, os, sys, subprocess, unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"

# Read the single source of truth
_pyproject = (_ROOT / "pyproject.toml").read_text()
_VERSION_LINE = None
for line in _pyproject.splitlines():
    if line.startswith("version"):
        _VERSION_LINE = line.split('"')[1]
        break

class TestVersionSync(unittest.TestCase):
    """api.py must read its version from pyproject.toml (no hardcoded drift)."""

    def setUp(self):
        self.api_src = (_SCRIPTS / "api.py").read_text()

    def test_no_hardcoded_version(self):
        # The old bug: VERSION = "2.5.0" hardcoded while pyproject said 2.7.0
        self.assertNotRegex(self.api_src, r'VERSION\s*=\s*"\d+\.\d+\.\d+"',
                            "api.py must not hardcode a version string")

    def test_reads_from_pyproject(self):
        self.assertIn("_read_version", self.api_src,
                      "api.py must define _read_version()")
        self.assertIn('VERSION = _read_version()', self.api_src)

    def test_runtime_version_matches_pyproject(self):
        # Actually import api.py and check the runtime value
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location(
                "_api_under_test", _SCRIPTS / "api.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except ImportError as e:
            if "fastapi" in str(e) or "uvicorn" in str(e):
                self.skipTest(f"fastapi/uvicorn not installed in this env: {e}")
            raise
        self.assertEqual(mod.VERSION, _VERSION_LINE,
                         f"runtime VERSION {mod.VERSION!r} != pyproject {_VERSION_LINE!r}")

class TestCLIInterface(unittest.TestCase):
    """CLI entry point: --version, --help, error handling."""

    PY = sys.executable

    def _run(self, *args):
        return subprocess.run(
            [self.PY, str(_SCRIPTS / "astro_cli.py"), *args],
            capture_output=True, text=True, timeout=60
        )

    def test_version_flag(self):
        r = self._run("--version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(_VERSION_LINE, r.stdout)

    def test_help_flag_exits_zero(self):
        r = self._run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hermes-astrology", r.stdout)

    def test_bad_json_to_stderr_nonzero(self):
        r = self._run("--json", "{not valid")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(len(r.stderr.strip()) > 0,
                        "errors must be written to stderr, not stdout")

    def test_summary_runs(self):
        r = self._run("--summary")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("=== WESTERN ===", r.stdout)

class TestDailyFetchTimezone(unittest.TestCase):
    """daily-astrology-fetch.py must report Tehran-local time, not UTC."""

    def test_uses_tehran_time(self):
        src = (_SCRIPTS / "daily-astrology-fetch.py").read_text()
        # utcnow() is the bug; must be gone or wrapped with Tehran tz
        self.assertNotIn("datetime.utcnow()", src,
                         "daily-astrology-fetch must not use datetime.utcnow()")

if __name__ == "__main__":
    unittest.main(verbosity=2)
