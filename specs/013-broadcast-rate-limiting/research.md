# Research — Broadcast Rate-Limiting & Reliability (013)

Phase 0. Все NEEDS CLARIFICATION спеки закрыты (FR-011 согласован с Шэфом). Ниже — принятые
технические решения с обоснованием и отклонёнными альтернативами.

## D-1. Обработка flood-wait (429)

- **Decision**: единый helper `_send_message_resilient(bot, **kwargs)` в `NotificationService`. Ловит
  `aiogram.exceptions.TelegramRetryAfter` → `await asyncio.sleep(min(e.retry_after, FLOOD_WAIT_CAP_SECONDS))`
  → повтор (до `FLOOD_WAIT_MAX_RETRIES` раз). Прочие `TelegramAPIError` (заблокировал бота и т.п.) →
  `logger.warning` + пропуск адресата (возврат без исключения). Через этот helper идут ОБЕ рассылки —
  `send_to_users` и каждый батч `send_native_all`.
- **Rationale**: одна точка политики повторов вместо двух копий (FR-002/FR-007). `TelegramRetryAfter`
  в aiogram 3 несёт `.retry_after` (секунды ожидания от Telegram) и является подклассом
  `TelegramAPIError`, поэтому порядок `except` важен: сначала `TelegramRetryAfter`, затем общий
  `TelegramAPIError`.
- **Cap на паузу** (`FLOOD_WAIT_CAP_SECONDS`): защита от абсурдно большого/битого `retry_after`
  (edge-case спеки) — не залипаем на минуты, не крутим busy-loop.
- **Alternatives rejected**: (а) внешняя библиотека троттлинга (`aiogram` middleware, `aiolimiter`) —
  нарушает «ноль новых зависимостей», избыточно для клубного масштаба; (б) глобальный лимитер токенов —
  сложнее и не нужен: последовательная отправка с малой паузой уже устраняет flood-wait на сотнях
  адресатов; (в) молчаливое проглатывание 429 (текущее поведение) — и есть чинимый дефект.

## D-2. Пауза между отправками

- **Decision**: кооперативная `await asyncio.sleep(BROADCAST_PACING_SECONDS)` между последовательными
  отправками в `send_to_users` и между батчами в `send_native_all`. Значение по умолчанию ~0.05 c.
- **Rationale**: R-DATA-7 — нельзя блокировать событийный цикл; `asyncio.sleep` уступает управление.
  0.05 c × сотни адресатов = единицы секунд, приемлемо для фоновых уведомлений и заметно снижает
  вероятность 429.
- **Alternatives rejected**: `time.sleep` (блокирует весь бот — прямое нарушение R-DATA-7); нулевая
  пауза (текущее поведение, провоцирует flood-wait).

## D-3. Батчинг @all

- **Decision**: `authorized_users` режется на чанки по `MENTION_BATCH_SIZE` (=50, лимит упоминаний
  Telegram на сообщение) через шаг `range(0, len, size)`; на каждый чанк — одно сообщение с скрытыми
  упоминаниями, отправка через `_send_message_resilient` с паузой между батчами.
- **Rationale**: покрывает всех авторизованных (FR-005/FR-006), устраняет тихий срез `[:50]`. Шаговый
  `range` естественно не создаёт пустой хвостовой батч при длине, кратной 50 (edge-case спеки).
- **Alternatives rejected**: одно сообщение с >50 упоминаниями (Telegram всё равно уведомит только
  первые ~50 — не решает проблему); отправка каждому персонально (шумно, ломает семантику «одно
  оповещение в топик», кратно дороже).

## D-4. Гейт @all (роль + кулдаун) — где живёт

- **Decision**: и роль, и кулдаун — внутри `NotificationService.send_native_all` (добавляется параметр
  `sender_id`). Роль: `PermissionService.is_moderator_of_topic(sender_id, topic_id) or
  PermissionService.is_global_admin(sender_id)`. Кулдаун: внутренний `_all_cooldown: dict[int, float]`,
  суперадмин освобождён (FR-011). При отказе — ранний возврат без рассылки; метка кулдауна пишется
  только после успешной рассылки.
- **Rationale**: централизует «массовое действие» за фасадом сервиса (FR-014), делает гейт полностью
  юнит-тестируемым без хендлера, а хендлер оставляет тонким (удалить триггер → вызвать сервис).
  Импорт `notification_service → permission_service` ацикличен (`permission_service` не импортирует
  `notification_service`), R-ARCH нарушения нет. Прецедент «сервис зовёт PermissionService» уже есть в
  `management_service`.
- **Alternatives rejected**: (а) проверка роли в хендлере (как `announcements.py`) — расщепляет решение
  между слоями (роль в хендлере, кулдаун в сервисе), хуже тестируется; (б) aiogram-фильтр на роль —
  фильтр не имеет доступа к кулдаун-состоянию и усложняет тихий отказ (нужно всё равно удалить триггер).

## D-5. Тихий отказ @all

- **Decision**: хендлер удаляет сообщение-триггер ВСЕГДА (как сейчас, для чистоты чата), затем зовёт
  сервис; при отказе сервис просто не рассылает и логирует. Никакого ответа в топик.
- **Rationale**: FR-010 + стиль stealth-модерации `AccessGuardMiddleware` (удаляет без публичного
  «отказано»). Публичный отказ демаскировал бы механизм и создавал шум.

## D-6. Кулдаун @all — в памяти, не персистентный

- **Decision**: `_all_cooldown` живёт в памяти процесса; после рестарта отсчёт с нуля.
- **Rationale**: анти-абьюз «мягкий» — в отличие от FSM-состояния (feature 012), терять его при
  рестарте безопасно (edge-case спеки). Персистентность потребовала бы схемы БД без реальной выгоды.
- **Кулдаун глобальный на отправителя** (не на топик) по умолчанию — строже и проще (Assumptions спеки).

## D-7. Ограничение роста `_alert_cache`

- **Decision**: `_prune_alert_cache(now)` в начале каждого алерт-метода удаляет записи с
  `now - ts > ALERT_CACHE_TTL_SECONDS` (=3600, максимальное из окон); сверх того — жёсткий потолок
  `ALERT_CACHE_MAX_ENTRIES` (при превышении вытесняются самые старые). Окна дедупа (60 c / 3600 c)
  остаются как есть.
- **Rationale**: запись старше максимального окна заведомо «протухла» — её удаление не меняет
  наблюдаемую защиту от повторов (после окна алерт и так был бы отправлен заново, FR-013). Это ограничивает
  память множеством «пар, виденных за последний час», а не всей историей (FR-012). Потолок — страховка
  на всплеск уникальных пар быстрее часа.
- **Alternatives rejected**: `functools.lru_cache`/`OrderedDict` LRU без учёта времени — усложняет и не
  привязан к семантике окна; отдельный фоновый сборщик — лишняя инфраструктура ради словаря на сотни
  ключей; TTL-словарь из внешнего пакета — новая зависимость.

## D-8. Константы

- **Decision**: все таймеры/размеры — module-level именованные константы в
  `services/notification_service.py` (FR-015). Проект не имеет общего `constants.py`; фича 010 держит
  свои тайминги и reset-хук в `management_service` — тот же паттерн.
- **Значения по умолчанию**: `BROADCAST_PACING_SECONDS=0.05`, `FLOOD_WAIT_CAP_SECONDS=30`,
  `FLOOD_WAIT_MAX_RETRIES=1`, `MENTION_BATCH_SIZE=50`, `ALL_MENTION_COOLDOWN_SECONDS=60`,
  `DEFAULT_DENY_WINDOW_SECONDS=60`, `MEMBER_DENY_WINDOW_SECONDS=3600`, `ALERT_CACHE_TTL_SECONDS=3600`,
  `ALERT_CACHE_MAX_ENTRIES=1000`. Финализируются на этапе реализации; поведение от «круглости» не зависит.

## D-9. Изоляция тестов

- **Decision**: `reset_notification_state()` в `notification_service` очищает `_alert_cache` и
  `_all_cooldown`; вызывается в `db_setup` (conftest) рядом с `reset_registration_cache` /
  `reset_sheets_sync_state`.
- **Rationale**: классовое/модульное состояние течёт между тестами (R-TEST-1). Паттерн уже устоялся в
  проекте (008/010).

## D-10. Симуляция 429 в тестах

- **Decision**: `mock_bot.send_message` — `AsyncMock` с `side_effect`, который на выбранных вызовах
  поднимает `TelegramRetryAfter(...)`, затем отдаёт успех. Проверяем: (а) была пауза/повтор и адресат
  в итоге получил сообщение; (б) `asyncio.sleep` вызван с ожидаемым (capped) значением — патчим
  `asyncio.sleep`, чтобы тест не ждал реально.
- **Rationale**: R-TEST-2 (никакой реальной сети), детерминизм, тест не висит на паузах.
- **Замечание по aiogram** (T001, сверено на установленной версии): aiogram **3.4.1**.
  `TelegramRetryAfter.__init__(self, method: TelegramMethod, message: str, retry_after: int)` — для
  подъёма в тесте нужен `method`, напр. `from aiogram.methods import SendMessage;
  TelegramRetryAfter(method=SendMessage(chat_id=1, text="x"), message="flood", retry_after=2)`.
  `TelegramRetryAfter` и `TelegramForbiddenError` — оба подклассы `TelegramAPIError`; поэтому в
  `_send_message_resilient` ветка `except TelegramRetryAfter` идёт ПЕРЕД `except TelegramAPIError`
  (иначе retry-after перехватится как общий сбой). `.retry_after` — целое, выставляется конструктором.
