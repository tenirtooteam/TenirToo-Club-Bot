import subprocess
import os
import sys
import tempfile

def run_linter(temp_dir, stage):
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "local_scripts", "prompt_linter.py"))
    # Run python with prompt_linter.py
    python_exe = sys.executable or "python"
    cmd = [python_exe, script_path, "--dir", temp_dir, "--stage", stage]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def test_journey_plan_linter():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Plan with errors (missing headers)
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Short Goal\nNo headers.")

        res = run_linter(tmpdir, "plan")
        assert res.returncode == 1
        assert "Error:" in res.stdout

        # 2. Plan with warnings (Cyrillic) but correct structure
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("""# Goal Description
Some description.

## User Review Required
Привет мир.

## Open Questions
None.

## Proposed Changes
### Component
#### [MODIFY] file.py

## Verification Plan
### Automated Tests
pytest
""")
        res = run_linter(tmpdir, "plan")
        assert res.returncode == 0
        assert "Warning:" in res.stdout

        # 3. Plan with no warnings/errors
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("""# Goal Description
Some description.

## User Review Required
None.

## Open Questions
None.

## Proposed Changes
### Component
#### [MODIFY] file.py

## Verification Plan
### Automated Tests
pytest
""")
        res = run_linter(tmpdir, "plan")
        assert res.returncode == 0
        assert "Warning:" not in res.stdout
        assert "Error:" not in res.stdout

def test_journey_checklist_linter():
    with tempfile.TemporaryDirectory() as tmpdir:
        checklist_path = os.path.join(tmpdir, "task.md")

        # 1. Checklist with incomplete task
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [ ] Task 2
- [x] запуск линтера-чеклиста
""")
        res = run_linter(tmpdir, "checklist")
        assert res.returncode == 1
        assert "Error: Incomplete task" in res.stdout

        # 2. Checklist missing linter step
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [x] Task 2
""")
        res = run_linter(tmpdir, "checklist")
        assert res.returncode == 1
        assert "Error: Last item must be" in res.stdout

        # 3. Correct checklist
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [x] Task 2
- [x] запуск линтера-чеклиста
""")
        res = run_linter(tmpdir, "checklist")
        assert res.returncode == 0
        assert "Checklist is valid" in res.stdout

def test_journey_report_linter():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "walkthrough.md")

        # 1. Report missing headers
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Walkthrough\nNo sections.")
        res = run_linter(tmpdir, "report")
        assert res.returncode == 1
        assert "Error: Missing required section" in res.stdout

        # 2. Report with warnings (no Russian/Cyrillic) but correct structure
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("""# Walkthrough
## Changes made
English only.

## What was tested
English only.

## Validation results
English only.
""")
        res = run_linter(tmpdir, "report")
        assert res.returncode == 0
        assert "Warning: No Cyrillic" in res.stdout

        # 3. Correct report
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("""# Walkthrough
## Changes made
Изменения на русском.

## What was tested
Тестирование проведено.

## Validation results
Результаты успешны.
""")
        res = run_linter(tmpdir, "report")
        assert res.returncode == 0
        assert "Warning:" not in res.stdout
        assert "Error:" not in res.stdout
