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

def test_journey_plan_legacy_rejected():
    """Spec-kit-only: a dir with only implementation_plan.md is rejected (no plan.md)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        legacy_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(legacy_path, "w", encoding="utf-8") as f:
            f.write("""# Goal Description
Some description.

## User Review Required
None.

## Proposed Changes
### Component
#### [MODIFY] file.py

## Verification Plan
pytest
""")
        res = run_linter(tmpdir, "plan")
        assert res.returncode == 1
        assert "no plan.md" in res.stdout

def test_journey_plan_v2_linter():
    """v2 CLI path: plan.md is preferred over implementation_plan.md end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "plan.md")

        # 1. v2 plan with errors (missing required H2s)
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Implementation Plan: X\nNo sections.")
        res = run_linter(tmpdir, "plan")
        assert res.returncode == 1
        assert "Error:" in res.stdout
        assert "Summary" in res.stdout

        # 2. Correct v2 plan
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("""# Implementation Plan: X

## Summary
Text.

## Technical Context
Text.

## Constitution Check
Text.

## Project Structure
Text.
""")
        res = run_linter(tmpdir, "plan")
        assert res.returncode == 0
        assert "Plan is valid" in res.stdout

def test_journey_checklist_legacy_rejected():
    """Spec-kit-only: a dir with only task.md is rejected (no tasks.md)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        legacy_path = os.path.join(tmpdir, "task.md")
        with open(legacy_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [x] запуск линтера-чеклиста
""")
        res = run_linter(tmpdir, "checklist")
        assert res.returncode == 1
        assert "no tasks.md" in res.stdout

def test_journey_checklist_v2_linter():
    """v2 CLI path: tasks.md is preferred over task.md end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        checklist_path = os.path.join(tmpdir, "tasks.md")

        # 1. v2 checklist with incomplete task
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [ ] Task 2
- [x] run checklist-linter
""")
        res = run_linter(tmpdir, "checklist")
        assert res.returncode == 1
        assert "Error: Incomplete task" in res.stdout

        # 2. Correct v2 checklist
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write("""- [x] Task 1
- [x] Task 2
- [x] run checklist-linter
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
