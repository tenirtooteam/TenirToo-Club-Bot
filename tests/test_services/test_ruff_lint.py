import subprocess
import sys
import os
import pytest

def test_ruff_linter():
    """
    [PL-6.24] [CC-2] Ruff Code Quality Check:
    Scan the codebase for common coding mistakes, syntax errors, and missing awaits.
    """
    import importlib.util
    if importlib.util.find_spec("ruff") is None:
        pytest.skip("ruff is not installed (skipping dev-only check)")

    # Resolve cross-platform path to the ruff executable
    if os.name == 'nt':
        ruff_path = os.path.join(sys.prefix, "Scripts", "ruff.exe")
    else:
        ruff_path = os.path.join(sys.prefix, "bin", "ruff")

    if not os.path.exists(ruff_path):
        pytest.skip(f"ruff binary not found at {ruff_path} (skipping dev-only check)")

    # Run the ruff check on the current directory
    result = subprocess.run(
        [ruff_path, "check", "."],
        capture_output=True,
        text=True
    )

    # Assert no violations were found
    assert result.returncode == 0, f"Ruff linter violations:\n{result.stdout}"
