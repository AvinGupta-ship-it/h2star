"""The published dataset must regenerate byte-for-byte from the committed
digitization inputs (route CSVs + re-inspection decisions) — referee
round-1 M7."""

import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_reconciliation_regenerates_dataset():
    r = subprocess.run(
        [sys.executable,
         os.path.join(ROOT, "scripts", "reconcile_digitization.py"),
         "--check"],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "byte-identical" in r.stdout
