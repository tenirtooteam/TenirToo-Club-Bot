# Файл: tests/test_services/test_semgrep_lint.py
"""
[PL-6.26] [CC-5] Semgrep Architecture Enforcement:
Проверяет кодовую базу набором кастомных Semgrep-правил из semgrep-rules.yaml.
Правила контролируют: запрет динамических импортов, изоляцию хэндлеров от БД,
запрет state.clear(), запрет прямых UI-вызовов и наличие параметра state.
"""
import subprocess
import sys
import os
import pytest


def test_semgrep_linter():
    """
    [PL-6.26] Semgrep Custom Rules Enforcement:
    Запускает semgrep scan с кастомными правилами проекта.
    Пропускается, если semgrep не установлен на хосте (dev-only проверка).
    """
    import importlib.util
    if importlib.util.find_spec("semgrep") is None:
        pytest.skip("semgrep is not installed (skipping dev-only check)")

    # Определяем путь к бинарнику semgrep кросс-платформенно
    if os.name == 'nt':
        semgrep_path = os.path.join(sys.prefix, "Scripts", "semgrep.exe")
    else:
        semgrep_path = os.path.join(sys.prefix, "bin", "semgrep")

    if not os.path.exists(semgrep_path):
        pytest.skip(f"semgrep binary not found at {semgrep_path} (skipping dev-only check)")

    # Путь к файлу правил относительно корня проекта
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rules_path = os.path.join(project_root, "semgrep-rules.yaml")

    if not os.path.exists(rules_path):
        pytest.skip(f"semgrep-rules.yaml not found at {rules_path}")

    # Запускаем сканирование Semgrep
    result = subprocess.run(
        [semgrep_path, "scan", "--config", rules_path, "--error", project_root],
        capture_output=True,
        text=True,
        cwd=project_root
    )

    # Проверяем отсутствие нарушений
    assert result.returncode == 0, (
        f"Semgrep обнаружил нарушения архитектурных правил:\n{result.stdout}\n{result.stderr}"
    )
