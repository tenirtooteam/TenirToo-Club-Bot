# Файл: tests/test_services/test_semgrep_lint.py
"""
[PL-6.26] [CC-5] Semgrep Architecture Enforcement:
Проверяет кодовую базу набором кастомных Semgrep-правил из semgrep-rules.yaml.
Правила контролируют: запрет динамических импортов, изоляцию хэндлеров от БД,
запрет state.clear(), запрет прямых UI-вызовов и наличие параметра state.
"""
import shutil
import subprocess
import sys
import os
import pytest


def _host_semgrep_cmd(project_root, rules_path):
    """Команда для нативного semgrep на хосте, либо None если он недоступен."""
    import importlib.util
    if importlib.util.find_spec("semgrep") is None:
        return None

    if os.name == 'nt':
        semgrep_path = os.path.join(sys.prefix, "Scripts", "semgrep.exe")
    else:
        semgrep_path = os.path.join(sys.prefix, "bin", "semgrep")

    if not os.path.exists(semgrep_path):
        return None

    return [semgrep_path, "scan", "--config", rules_path, "--error", project_root]


def _docker_semgrep_cmd():
    """Команда для контейнеризированного semgrep (R-PROC-11), либо None если Docker недоступен."""
    if shutil.which("docker") is None:
        return None
    return [
        "docker", "compose", "--profile", "lint",
        "run", "--rm", "semgrep",
    ]


def test_semgrep_linter():
    """
    [PL-6.26] Semgrep Custom Rules Enforcement:
    Запускает semgrep scan с кастомными правилами проекта.

    Порядок выбора движка: нативный semgrep на хосте → контейнеризированный
    semgrep через Docker Compose (R-PROC-11). Пропускается только когда
    недоступны оба варианта (например, win32 без установленного Docker).
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rules_path = os.path.join(project_root, "semgrep-rules.yaml")

    if not os.path.exists(rules_path):
        pytest.skip(f"semgrep-rules.yaml not found at {rules_path}")

    cmd = _host_semgrep_cmd(project_root, rules_path) or _docker_semgrep_cmd()
    if cmd is None:
        pytest.skip("neither native semgrep nor Docker is available (skipping SAST gate)")

    # Запускаем сканирование Semgrep выбранным движком
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=project_root
    )

    # Проверяем отсутствие нарушений
    assert result.returncode == 0, (
        f"Semgrep обнаружил нарушения архитектурных правил:\n{result.stdout}\n{result.stderr}"
    )
