# Contracts — NotificationService & @all handler (013)

Внутренние контракты слоя рассылок. «Публичного» API наружу нет; контракт = сигнатуры сервисных
методов и наблюдаемое поведение хендлера.

## C-1. `NotificationService.send_to_users` (сигнатура НЕ меняется)

~~~python
@staticmethod
async def send_to_users(bot: Bot, user_ids: list[int], text: str, reply_markup=None) -> None
~~~

- **Контракт (новый, поведенческий)**:
  - дедуп по `set(user_ids)` сохранён;
  - каждая отправка идёт через `_send_message_resilient` (429 → пауза≤cap + повтор; прочее → log+skip);
  - между отправками — `asyncio.sleep(BROADCAST_PACING_SECONDS)`;
  - недоступный адресат НЕ прерывает рассылку (FR-003).
- **Совместимость**: единственный вызывающий — `ManagementService` (`management_service.py:760`,
  аудит-заявки) — правок не требует.

## C-2. `NotificationService.send_native_all` (ДОБАВЛЯЕТСЯ `sender_id`)

~~~python
@staticmethod
async def send_native_all(
    bot: Bot, sender_id: int, chat_id: int, topic_id: int, sender_name: str, text: str
) -> None
~~~

- **Гейт (FR-009/FR-011)** — до любой отправки:
  1. роль: `is_moderator_of_topic(sender_id, topic_id) or is_global_admin(sender_id)`; иначе — выход
     без рассылки (лог);
  2. кулдаун (не для суперадмина): `now - _all_cooldown.get(sender_id, 0) <= ALL_MENTION_COOLDOWN_SECONDS`
     ⇒ выход без рассылки.
- **Рассылка (FR-005..008)**: пустой `authorized_users` → выход (0 сообщений); иначе — батчи по
  `MENTION_BATCH_SIZE`, по сообщению на батч через `_send_message_resilient`, пауза между батчами; НЕТ
  среза `[:50]`.
- **Пост-условие**: при успешной рассылке модератором — `_all_cooldown[sender_id] = now`.
- **Совместимость**: единственный вызывающий — `handlers/user.py:handle_all_mention` — добавляет
  аргумент `sender_id=message.from_user.id`.

## C-3. `handle_all_mention` (handlers/user.py) — наблюдаемое поведение

- Порядок: удалить сообщение-триггер (`UIService.delete_msg`) ВСЕГДА → подготовить `clean_text` →
  вызвать `send_native_all(..., sender_id=message.from_user.id, ...)`.
- **Тихий отказ (FR-010)**: при недостатке роли/кулдауне бот НЕ пишет в топик; отличие от разрешённого
  вызова — только отсутствие рассылки.

## C-4. Приватные помощники (новые)

~~~python
@staticmethod
async def _send_message_resilient(bot: Bot, **send_kwargs) -> bool
    # True при доставке, False при финальном отказе; сам обрабатывает 429 и логирует.

@classmethod
def _prune_alert_cache(cls, now: float) -> None
    # удаляет протухшие (> ALERT_CACHE_TTL_SECONDS) и держит размер <= ALERT_CACHE_MAX_ENTRIES.
~~~

## C-5. Хук изоляции тестов (новый)

~~~python
def reset_notification_state() -> None
    # NotificationService._alert_cache.clear(); NotificationService._all_cooldown.clear()
~~~

Вызывается в `tests/conftest.py::db_setup` рядом с `reset_registration_cache()` /
`reset_sheets_sync_state()`.

## Тестовые проверки контракта (R-TEST-3: args + kwargs)

- `send_to_users`: при 429 на N-й отправке — `asyncio.sleep` вызван с capped-значением, адресат
  получил сообщение повтором; дубликаты не дублируют отправку.
- `send_native_all`: 120 авторизованных → 3 сообщения (50/50/20), каждый UID упомянут ровно раз;
  негативный путь — не-модератор → 0 сообщений; повтор < cooldown → 0 сообщений; суперадмин игнорирует
  cooldown.
- `_alert_cache`: после серии протухших пар размер ограничен; подавление в пределах окна сохранено.
