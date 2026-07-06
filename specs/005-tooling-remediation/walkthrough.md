# Walkthrough — Feature 005: AI Tooling Remediation

Отчёт по исполнению. Язык — русский (R-PROC-8). Английские термины/пути допустимы.

## Baseline (Phase 1, до фиксов)

**T001 — репродукция бага коллекции pytest**
- `.\venv\Scripts\pytest -q --collect-only` → **FAIL**: `ImportError while loading conftest ... ModuleNotFoundError: No module named 'database'` (корень проекта не в `sys.path`).
- `.\venv\Scripts\python -m pytest -q` → **BASELINE = 122 passed, 1 skipped, 16 warnings** (16.4s).

**T002 — репродукция ложного срабатывания линтера (plan-stage)**
- specs/001 → `Warning: Cyrillic words found in plan: -`
- specs/002 → `Warning: Cyrillic words found in plan: -`
- specs/003 → `Warning: Cyrillic words found in plan: -, ?-`
- specs/004 → `Warning: Cyrillic words found in plan: -`
- Все 4 плана валидны по структуре; предупреждение вызвано пунктуацией (дефис), а не реальной кириллицей — подтверждает баг US4.

**T003 — регресс-гварды до изменений**
- `ruff check .` → **All checks passed!**
- `lint-imports` → **Contracts: 1 kept, 0 broken** (Sterile Presentation Layer KEPT).

---

## Phase 2 — Foundational (канонический вызов pytest)

**T004a — failing-first smoke-тест (R-PROC-3)**
- `tests/test_services/test_collection_smoke.py`: subprocess `pytest --collect-only`, assert rc==0.
- До pytest.ini: **FAIL** (rc 4, `ModuleNotFoundError: database`) — баг воспроизведён автоматически.

**T004 — `pytest.ini`** создан: `pythonpath = .`, `testpaths = tests`.

**T005 — верификация фикса**
- `.\venv\Scripts\pytest -q` (голый бинарь, раньше падал) → **122 passed, 1 skipped**.
- `.\venv\Scripts\python -m pytest -q` → **122 passed, 1 skipped** (без регресса).
- Smoke-тест отдельно → **1 passed** (rc 0 после pytest.ini).
- collect-only → **123 tests collected**.

**⚠️ Важное расхождение с BASELINE (разобрано, покрытие не потеряно):**
BASELINE `python -m pytest` собирал `123` = tests/ (121 passed + 1 skipped) **плюс**
`scratch/test_help_service.py` (1 passed, вне tests/). После `testpaths = tests` scratch
исключён, добавлен smoke → снова 122 passed + 1 skipped (совпадение чисел).
`scratch/` — **gitignored** (`.gitignore:42`), не отслеживается; файл — ручной print-скрипт
без ассертов (`if __name__ == "__main__"`), не настоящий pytest-тест. Исключение
корректно и предусмотрено планом (гвард testpaths против scratch/_nogit). Реального
покрытия не утрачено.

---

## US1 — Канонический вызов во всех живых доках (T007–T008)

**T007 — свип живых доков** (specs/001-005, `_nogit_*`, `.pytest_cache` — вне зоны):
- `docs/knowledge/subagents.md:31` — `Runs pytest tests using .\venv\Scripts\pytest`. **Уже
  каноничен**: наш pytest.ini сделал эту форму рабочей → правка не нужна (ретроактивно верна).
- `docs/knowledge/testing.md` — явной команды запуска не было → добавлена секция «Running the Suite».
- `README.md:202` — `docker compose run --rm app pytest` — отдельный Docker-канал, корректен, оставлен.
- `RULES.md`, `AGENTS.md`, `architecture.md`, `features-overview.md` — «pytest» только как
  описание стека/правил, не форма вызова → без изменений.
- **Вывод**: ни один живой док больше не предписывает сломанную форму.

**T008 — правка**: `docs/knowledge/testing.md` — новая секция «Running the Suite (Canonical
Invocation)» с формой `.\venv\Scripts\pytest`, объяснением pytest.ini (pythonpath/testpaths),
эквивалентностью `python -m pytest` и Docker-каналом.

---

## US2 — Plugin-регистрация (T011–T014)

**T011 — сверка механики** (Claude Code 2.1.185):
- Есть `claude plugin marketplace add <source> --scope project|user|local` и `claude plugin
  install <plugin>@<mkt> --scope project`, `claude plugin validate <path> --strict`.
- Маркетплейсов не было. Механизм: `.claude-plugin/marketplace.json` (источник) →
  `extraKnownMarketplaces` + `enabledPlugins` в settings.

**T012 — манифест плагина**: `.agents/plugins/tenirtoo-plugin/.claude-plugin/plugin.json`
(name/version 2.0.0/description/author); плоский `plugin.json` удалён. `validate --strict` → **passed**.

**T013 — маркетплейс**: корневой `.claude-plugin/marketplace.json` (tenirtoo-local →
плагин по относительному пути `./.agents/plugins/tenirtoo-plugin`). `validate --strict` → **passed**.

**T014 — подключение (project scope)** через CLI (авторитетный формат для версии):
- `marketplace add ./ --scope project` → добавлен `tenirtoo-local`.
- `install tenirtoo-plugin@tenirtoo-local --scope project` → **enabled**, version 2.0.0.
- `.claude/settings.json` дописан **аддитивно**: `env`/`hooks` (графифай) целы, добавлены
  `extraKnownMarketplaces` + `enabledPlugins`. Проверено `plugin list` → ✔ enabled.

**Ярус хранения (Local, консистентно с FILE REGISTRY):**
- `.agents/` gitignored (стр. 29) → плагин Local; `.claude/` gitignored (стр. 32) → settings Local.
- `.claude-plugin/marketplace.json` был untracked-и-не-ignored → добавлен `.claude-plugin/`
  в `.gitignore` (стр. 30), чтобы весь механизм регистрации жил в одном Local-ярусе.
- CLI записал абсолютный `path` маркетплейса — приемлемо, т.к. файл локальный (не в git).
- **Воспроизведение на новом клоне** (плагин Local): выполнить
  `claude plugin marketplace add ./ --scope project` + `claude plugin install
  tenirtoo-plugin@tenirtoo-local --scope project`.

---

## US3 — Делегируемые сабагенты (T019–T023)

**T019–T021 — три агент-файла** в `.agents/plugins/tenirtoo-plugin/agents/`:
- `proposal-auditor.md`, `test-runner-and-debugger.md`, `cognitive-ux-auditor.md` —
  сгенерированы из `subagents.md` §§1-3, формат Claude Code (frontmatter + system prompt).
- **Дельты от источника (только infra):** (a) `test-runner` использует канонический
  `.\venv\Scripts\pytest` — совпадает с источником, FR-008 выполнен копией; (b) одна строка
  graphify-first (R-PROC-12) на агентах, исследующих код — этого требует хук в settings.json.
- `test-runner` получил `tools: Bash, Read, Edit, Grep, Glob`; `cognitive-ux-auditor` —
  `Bash, Read, Grep, Glob` (без Edit — только аудит); запрет правки тестов/конфигов в теле.

**Верификация структуры**: `claude plugin validate --strict` → **passed**;
`claude plugin details tenirtoo-plugin` → инвентарь **Skills (2): docs-update,
proposal-analysis; Agents (3): cognitive-ux-auditor, proposal-auditor,
test-runner-and-debugger**. Harness распознаёт все 5 компонентов.

**T022 — mirror-note**: в `subagents.md` добавлена пометка, что файл — описательный источник,
а `.agents/plugins/tenirtoo-plugin/agents/*.md` — операционное зеркало (с указанием двух
infra-дельт). Governance+bundle **12 passed**, full **122/1** — без регресса.

**T023 — fresh-session проверка**: отложена на совместный прогон с T016 (вариант B) —
см. HARD STOP T024.

---

## US4 — Линтер без ложных срабатываний (T025–T027)

**T025 — failing-first**: изначально отдельный файл дал коллизию имён с существующим
каноническим `tests/test_prompt_linter.py` (import file mismatch — в проекте нет `__init__`
в test-каталогах). Дубль удалён, **3 регресс-кейса влиты в канонический модуль** (single
source): дефисная латиница/даты, пунктуация-only, смешанный `спек-kit`. Кейсы для
настоящего рус.слова и whitelist уже покрыты `test_validate_plan_cyrillic_warning`. До
фикса добавленные кейсы падали (дефисы флагались).

**T026 — фикс** (`local_scripts/prompt_linter.py`): токен считается нарушением только если
содержит ≥1 кириллическую букву (регексп `cyrillic_letter.search`), пунктуационные токены
(`-`, `--`) пропускаются. Дефис в классе оставлен, чтобы не разрывать `Теңир-Тоо`.

**T027 — верификация**:
- Линтер-тесты → **5 passed**.
- plan-stage по specs 001–005: ложные `-` исчезли везде. Остался ОДИН флаг у **003**:
  токен `К-` (`U+041A`, кириллическая «К» вместо латинской в «K-group», строки 9/31 плана).
  Это **истинный** положительный результат — реальная кириллица в легаси-плане, а не ложный.
  Служит живым доказательством дискриминации (SC-002: ложных нет, настоящее флагается).
  003 — read-only исторический запись, не правится.

---

## US5 — SAST-гейт semgrep (T029–T032)

- **T029**: `docker-compose.yml` — профиль `lint` уже присутствует (строки 23-24), правка не нужна.
- **T030 — Semgrep gate**: Docker Desktop поднят; `docker compose --profile lint run --rm
  semgrep` → **Scan completed successfully. Findings: 0 (0 blocking). Rules run: 5. Targets:
  46. exit 0**. Гейт верифицирован зелёным (FR-009, SC-004).
- **T031**: `requirements-dev.txt` → `semgrep>=1.65.0; sys_platform != "win32"`;
  `pip install --dry-run` на win32 проходит без попытки ставить semgrep (FR-010).
- **T032**: `docs/knowledge/testing.md` — секция «Architecture SAST gate (semgrep)»: Docker —
  канонический канал, host-`test_semgrep_lint.py` skip на Windows — намеренное поведение.
  Governance+bundle 12 passed.

---

## US6 — Мёртвые ссылки (T034–T035)

- **T034**: из `CLAUDE.md` удалена строка про `graphify-out/wiki/index.md` (CLI graphify
  0.8.49 wiki не производит) (FR-011).
- **T035 — свип**: в живых агент-facing доках (CLAUDE/AGENTS/RULES/GEMINI/docs/knowledge)
  wiki-ссылок больше нет; все `graphify-out/*` ссылки (`.graphify_python`, `GRAPH_REPORT.md`,
  `graph.json`) указывают на существующие артефакты; удалённых легаси-файлов
  (PROJECT_LOGIC/CONTEXT_PROMPT) в шимах/конституции нет. SC-005 ✅.

---

## Changes made

- `pytest.ini` [NEW] — pythonpath=., testpaths=tests.
- `CLAUDE.md` [MODIFY] — удалена мёртвая ссылка на graphify wiki.
- `tests/test_prompt_linter.py` [MODIFY] — +3 регресс-кейса языковой проверки (слиты в канонический модуль).
- `local_scripts/prompt_linter.py` [MODIFY] — фильтр «≥1 кириллическая буква».
- `requirements-dev.txt` [MODIFY] — маркер `; sys_platform != "win32"` на semgrep.
- `docs/knowledge/testing.md` [MODIFY] — секция SAST-гейта (Docker-канал + Windows-skip).
- `tests/test_services/test_collection_smoke.py` [NEW] — регресс-гвард канонического вызова.
- `docs/knowledge/testing.md` [MODIFY] — секция канонического запуска.
- `.agents/plugins/tenirtoo-plugin/.claude-plugin/plugin.json` [NEW]; плоский `plugin.json` удалён.
- `.agents/plugins/tenirtoo-plugin/agents/{proposal-auditor,test-runner-and-debugger,cognitive-ux-auditor}.md` [NEW].
- `.claude-plugin/marketplace.json` [NEW, Local]; `.claude/settings.json` [MODIFY, Local, аддитивно].
- `.gitignore` [MODIFY] — добавлен `.claude-plugin/`.
- `docs/knowledge/subagents.md` [MODIFY] — mirror-note.

## What was tested

- Foundational: см. T004a/T004/T005 выше.
- US1: свип доков (T007), выравнивание testing.md (T008), регресс-гейт (T009).
- US2/US3: `plugin validate --strict` + `plugin details` (5 компонентов), fresh-session (Шэф подтвердил).
- US4: линтер-модуль 22 passed, plan-stage по 001–005.
- US5: semgrep Docker gate 0 findings; pip --dry-run win32.
- Polish: scope-guard (T036), полная регрессия (T037).

## Validation results

- Канонический `.\venv\Scripts\pytest` работает из корня; `python -m pytest` без регресса.
- **T036 scope guard**: `git diff HEAD -- handlers services middlewares database keyboards web`
  → пусто; untracked продакшена нет (FR-012, SC-006 ✅).
- **T037 финальная регрессия**: pytest **125 passed, 1 skipped**; `ruff` — All checks passed;
  `lint-imports` — 1 kept, 0 broken. `graphify update .` (AST-only) → 1845 nodes, 3140 edges.
