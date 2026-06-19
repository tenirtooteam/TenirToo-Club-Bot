import pytest
import sys
import os

# Adjust path to find local_scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_scripts.prompt_linter import (
    validate_plan,
    validate_checklist,
    validate_report,
)

def test_validate_plan_success():
    content = """# Goal Description
Some description here.

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
"""
    errors, warnings = validate_plan(content)
    assert not errors
    assert not warnings

def test_validate_plan_missing_sections():
    content = """# Goal Description
No other headers.
"""
    errors, warnings = validate_plan(content)
    assert len(errors) > 0
    assert any("User Review Required" in e for e in errors)
    assert any("Open Questions" in e for e in errors)
    assert any("Proposed Changes" in e for e in errors)
    assert any("Verification Plan" in e for e in errors)

def test_validate_plan_cyrillic_warning():
    content = """# Goal Description
This is English text.

## User Review Required
Русский текст вызывает варнинг.
Но слово Шэф в вайтлисте.
И слово Теңир-Тоо тоже.

## Open Questions
None.

## Proposed Changes
### Component
#### [MODIFY] file.py

## Verification Plan
### Automated Tests
pytest
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
