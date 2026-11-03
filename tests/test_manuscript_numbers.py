"""D10: the manuscript's macro file must match freshly generated numbers."""

import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
MACROS = os.path.join(ROOT, "manuscript", "generated_numbers.tex")


@pytest.mark.skipif(not os.path.exists(MACROS),
                    reason="manuscript macros not generated yet")
def test_macros_match_regeneration():
    res = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "reproduce_paper.py"),
         "--check"], capture_output=True, text=True)
    assert res.returncode == 0, (
        "manuscript/generated_numbers.tex disagrees with regeneration:\n"
        + res.stdout + res.stderr)
