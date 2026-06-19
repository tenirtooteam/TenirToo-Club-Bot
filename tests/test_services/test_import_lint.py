import subprocess
import sys
import os
import pytest

def test_import_linter():
    """
    [PL-6.24] [CC-2] Import Boundary Checking:
    Verify that presentation layers (handlers, middlewares) do not directly import
    database facade or modules, using import-linter.
    """
    import importlib.util
    if importlib.util.find_spec("importlinter") is None:
        pytest.skip("import-linter is not installed (skipping dev-only check)")

    # Resolve cross-platform path to the lint-imports executable
    if os.name == 'nt':
        lint_imports_path = os.path.join(sys.prefix, "Scripts", "lint-imports.exe")
    else:
        lint_imports_path = os.path.join(sys.prefix, "bin", "lint-imports")

    # Verify binary exists
    if not os.path.exists(lint_imports_path):
        pytest.skip(f"lint-imports binary not found at {lint_imports_path} (skipping dev-only check)")

    # Run the import linter
    result = subprocess.run(
        [lint_imports_path],
        capture_output=True,
        text=True
    )

    # Assert that no contract violations were detected
    assert result.returncode == 0, f"Import linter contract violations:\n{result.stdout}"
