# Файл: tests/test_services/test_collection_smoke.py
"""
[R-PROC-3] [feature 005] Canonical pytest invocation smoke test:
Воспроизводящий тест для бага сбора (collection): при запуске «голого» бинаря
`pytest` (а не `python -m pytest`) корень проекта не попадает в sys.path, и
tests/conftest.py падает с `ModuleNotFoundError: No module named 'database'`.
Тест запускает `pytest --collect-only` подпроцессом и требует код возврата 0.
До появления pytest.ini (pythonpath = .) — ПАДАЕТ; после — зелёный.
Служит регресс-гвардом канонической формы вызова тестов (contracts/canonical-test-invocation.md).
"""
import subprocess
import sys
import os


def test_bare_pytest_collects_from_root():
    """
    [R-PROC-3] Канонический вызов `.\\venv\\Scripts\\pytest` собирает набор без
    ImportError. Гвард против регрессии конфигурации sys.path/rootdir.
    """
    # Путь к «голому» бинарю pytest внутри активного venv, кросс-платформенно
    if os.name == "nt":
        pytest_path = os.path.join(sys.prefix, "Scripts", "pytest.exe")
    else:
        pytest_path = os.path.join(sys.prefix, "bin", "pytest")

    if not os.path.exists(pytest_path):
        # На нестандартном окружении бинарь может отсутствовать — не проваливаем прогон
        import pytest
        pytest.skip(f"pytest binary not found at {pytest_path}")

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Чистое окружение без унаследованного PYTHONPATH, чтобы не «протащить» корень мимо pytest.ini
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [pytest_path, "--collect-only", "-q"],
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert result.returncode == 0, (
        "Голый `pytest --collect-only` не собрал набор — корень проекта не в sys.path "
        f"(нужен pytest.ini с pythonpath = .):\n{result.stdout}\n{result.stderr}"
    )
