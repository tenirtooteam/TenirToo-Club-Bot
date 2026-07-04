import sys
import os
import tempfile

# Adjust path to find local_scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_scripts.prompt_linter import (
    validate_plan,
    validate_checklist,
    validate_report,
    find_plan_file,
    find_checklist_file,
    PLAN_V2_REQUIRED_H2S,
)

def test_validate_plan_success():
    # Default structure is now the spec-kit plan.md (v2) — legacy RNA headers removed.
    content = """# Implementation Plan: Feature X

## Summary
Some summary here.

## Technical Context
Details.

## Constitution Check
Passes.

## Project Structure
### Documentation (this feature)
Tree.
"""
    errors, warnings = validate_plan(content)
    assert not errors
    assert not warnings

def test_validate_plan_missing_sections():
    content = """# Implementation Plan: Feature X
No other headers.
"""
    errors, warnings = validate_plan(content)
    assert len(errors) > 0
    assert any("Summary" in e for e in errors)
    assert any("Technical Context" in e for e in errors)
    assert any("Constitution Check" in e for e in errors)
    assert any("Project Structure" in e for e in errors)

def test_validate_plan_cyrillic_warning():
    content = """# Implementation Plan: Feature X

## Summary
This is English text.

## Technical Context
Русский текст вызывает варнинг.
Но слово Шэф в вайтлисте.
И слово Теңир-Тоо тоже.

## Constitution Check
Passes.

## Project Structure
### Documentation (this feature)
Tree.
"""
    errors, warnings = validate_plan(content)
    assert not errors
    assert len(warnings) > 0
    assert any("Русский" in w for w in warnings)
    assert not any("Шэф" in w for w in warnings)
    assert not any("Теңир-Тоо" in w for w in warnings)

def test_validate_checklist_success():
    content = """- [x] task 1
- [x] task 2
- [x] запуск линтера-чеклиста
"""
    errors, warnings = validate_checklist(content)
    assert not errors
    assert not warnings

def test_validate_checklist_pending_error():
    content = """- [x] task 1
- [/] task 2 in progress
- [ ] task 3 pending
- [x] запуск линтера-чеклиста
"""
    errors, warnings = validate_checklist(content)
    assert len(errors) > 0
    assert any("incomplete" in e.lower() for e in errors)

def test_validate_checklist_missing_linter_step():
    content = """- [x] task 1
- [x] task 2
"""
    errors, warnings = validate_checklist(content)
    assert len(errors) > 0
    assert any("last item" in e.lower() for e in errors)

def test_validate_checklist_no_tasks():
    content = ""
    errors, warnings = validate_checklist(content)
    assert len(errors) > 0

def test_validate_report_success():
    content = """# Walkthrough
## Changes made
Сделали изменения тут и там.

## What was tested
Протестировано ручками.

## Validation results
Все тесты прошли.
"""
    errors, warnings = validate_report(content)
    assert not errors
    assert not warnings

def test_validate_report_missing_sections():
    content = """# Walkthrough
## Some other section
"""
    errors, warnings = validate_report(content)
    assert len(errors) > 0
    assert any("Changes made" in e for e in errors)

def test_validate_plan_v2_structure_success():
    content = """# Implementation Plan: Feature X

**Branch**: `x` | **Date**: 2026-07-03 | **Spec**: link

## Summary
Some summary.

## Technical Context
Details.

## Constitution Check
Passes.

## Project Structure
### Documentation (this feature)
Tree.
"""
    errors, warnings = validate_plan(content, required_h2s=PLAN_V2_REQUIRED_H2S)
    assert not errors

def test_validate_plan_v2_structure_missing_sections():
    content = """# Implementation Plan: Feature X
No other headers.
"""
    errors, warnings = validate_plan(content, required_h2s=PLAN_V2_REQUIRED_H2S)
    assert len(errors) > 0
    assert any("Summary" in e for e in errors)
    assert any("Technical Context" in e for e in errors)
    assert any("Constitution Check" in e for e in errors)
    assert any("Project Structure" in e for e in errors)

def test_plan_v2_speckit_file():
    """find_plan_file prefers plan.md (v2) when it is the only plan artifact present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "plan.md"), "w", encoding="utf-8") as f:
            f.write("# Plan\n## Summary\n")
        path, is_v2 = find_plan_file(tmpdir)
        assert is_v2 is True
        assert os.path.basename(path) == "plan.md"

def test_plan_legacy_rejected():
    """Legacy implementation_plan.md is no longer accepted — spec-kit-only Route A."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "implementation_plan.md"), "w", encoding="utf-8") as f:
            f.write("# Goal Description\n")
        path, is_v2 = find_plan_file(tmpdir)
        assert path is None

def test_plan_ignores_legacy_when_both_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "plan.md"), "w", encoding="utf-8") as f:
            f.write("# Plan\n")
        with open(os.path.join(tmpdir, "implementation_plan.md"), "w", encoding="utf-8") as f:
            f.write("# Goal Description\n")
        path, is_v2 = find_plan_file(tmpdir)
        assert is_v2 is True
        assert os.path.basename(path) == "plan.md"

def test_checklist_v2_tasks_file():
    """find_checklist_file prefers tasks.md (v2) when it is the only checklist artifact present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [x] запуск линтера-чеклиста\n")
        path, is_v2 = find_checklist_file(tmpdir)
        assert is_v2 is True
        assert os.path.basename(path) == "tasks.md"

def test_checklist_legacy_rejected():
    """Legacy task.md is no longer accepted — spec-kit-only Route A."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "task.md"), "w", encoding="utf-8") as f:
            f.write("- [x] запуск линтера-чеклиста\n")
        path, is_v2 = find_checklist_file(tmpdir)
        assert path is None

def test_checklist_ignores_legacy_when_both_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("- [x] запуск линтера-чеклиста\n")
        with open(os.path.join(tmpdir, "task.md"), "w", encoding="utf-8") as f:
            f.write("- [x] запуск линтера-чеклиста\n")
        path, is_v2 = find_checklist_file(tmpdir)
        assert is_v2 is True
        assert os.path.basename(path) == "tasks.md"

def test_find_plan_file_none_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        path, is_v2 = find_plan_file(tmpdir)
        assert path is None
        assert is_v2 is None

def test_validate_report_missing_russian_warning():
    content = """# Walkthrough
## Changes made
Only English text here.

## What was tested
No Russian here either.

## Validation results
Success.
"""
    errors, warnings = validate_report(content)
    assert not errors
    assert len(warnings) > 0
    assert any("Cyrillic" in w or "Russian" in w for w in warnings)
