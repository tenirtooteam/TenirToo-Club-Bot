"""Тесты рассылок (feature 013, №18 + №5).

Все Telegram-вызовы мокаются (R-TEST-2); классовое состояние сбрасывается фикстурой db_setup
через reset_notification_state() (R-TEST-1). asyncio.sleep патчится, чтобы тесты не ждали реально.
"""
import re
import time
import pytest
from unittest.mock import AsyncMock, patch, call

from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from aiogram.methods import SendMessage

from services.notification_service import (
    NotificationService,
    BROADCAST_PACING_SECONDS,
    FLOOD_WAIT_CAP_SECONDS,
    MENTION_BATCH_SIZE,
    DEFAULT_DENY_WINDOW_SECONDS,
    ALERT_CACHE_TTL_SECONDS,
    ALERT_CACHE_MAX_ENTRIES,
)

_DUMMY_METHOD = SendMessage(chat_id=1, text="x")


def _retry_after(seconds: int) -> TelegramRetryAfter:
    return TelegramRetryAfter(method=_DUMMY_METHOD, message="flood", retry_after=seconds)


def _forbidden() -> TelegramForbiddenError:
    return TelegramForbiddenError(method=_DUMMY_METHOD, message="bot was blocked by the user")


def _sent_chat_ids(mock_bot) -> list[int]:
    """chat_id из всех вызовов send_message (в порядке вызова)."""
    return [c.kwargs.get("chat_id", (c.args[0] if c.args else None)) for c in mock_bot.send_message.call_args_list]


# --- US1: send_to_users надёжность под flood-wait ---

@pytest.mark.asyncio
async def test_send_to_users_survives_flood_wait(mock_bot, db_setup):
    """FR-002: первый 429 -> ждём retry_after (capped) и повторяем; адресат в итоге доставлен,
    список доходит до конца."""
    calls = {"n": 0}

    async def flood_first(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _retry_after(2)
        return None

    mock_bot.send_message.side_effect = flood_first

    with patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await NotificationService.send_to_users(mock_bot, [10, 20, 30], "hello")

    # 3 адресата + 1 повтор после flood = 4 вызова; все три chat_id присутствуют.
    assert mock_bot.send_message.call_count == 4
    assert set(_sent_chat_ids(mock_bot)) == {10, 20, 30}
    # Пауза flood-wait = min(retry_after, cap) = 2 c.
    assert call(min(2, FLOOD_WAIT_CAP_SECONDS)) in mock_sleep.call_args_list


@pytest.mark.asyncio
async def test_send_to_users_paces_between_sends(mock_bot, db_setup):
    """FR-001/FR-004: пауза BROADCAST_PACING_SECONDS между отправками; дедуп set()."""
    with patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await NotificationService.send_to_users(mock_bot, [1, 1, 2], "hi")

    # Дедуп: 2 уникальных адресата -> 2 отправки.
    assert mock_bot.send_message.call_count == 2
    assert set(_sent_chat_ids(mock_bot)) == {1, 2}
    # Между отправками была кооперативная пауза заданной величины.
    assert call(BROADCAST_PACING_SECONDS) in mock_sleep.call_args_list


@pytest.mark.asyncio
async def test_send_to_users_skips_unreachable(mock_bot, db_setup):
    """FR-003: недоступный адресат (заблокировал бота) логируется и пропускается,
    остальные доставлены; исключение наружу не всплывает."""
    async def forbidden_for_20(**kwargs):
        if kwargs.get("chat_id") == 20:
            raise _forbidden()
        return None

    mock_bot.send_message.side_effect = forbidden_for_20

    with patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock):
        # Не должно поднять исключение.
        await NotificationService.send_to_users(mock_bot, [10, 20, 30], "hello")

    # Все три попытки сделаны; 10 и 30 доставлены (forbidden только у 20).
    assert set(_sent_chat_ids(mock_bot)) == {10, 20, 30}


# --- US2: send_native_all батчи (покрытие всех авторизованных) ---

def _authorized(n: int) -> list[tuple]:
    """n авторизованных пользователей формата (id, first_name, last_name)."""
    return [(i, f"User{i}", "") for i in range(1, n + 1)]


def _mentioned_ids(mock_bot) -> set[int]:
    """Все id из скрытых упоминаний по всем отправленным сообщениям."""
    ids: set[int] = set()
    for c in mock_bot.send_message.call_args_list:
        text = c.kwargs.get("text", "")
        ids.update(int(x) for x in re.findall(r"tg://user\?id=(\d+)", text))
    return ids


def _moderator():
    """Отправитель @all — авторизованный модератор (гейт US3 форвард-совместимо пропускает)."""
    return patch(
        "services.permission_service.PermissionService.is_moderator_of_topic",
        return_value=True,
    )


@pytest.mark.asyncio
async def test_send_native_all_covers_all_authorized(mock_bot, db_setup):
    """FR-005/FR-006: 120 авторизованных -> 3 батча (50/50/20), упомянуты все 120."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(120)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=777, chat_id=-100, topic_id=5, sender_name="Mod", text="hi"
        )

    assert mock_bot.send_message.call_count == 3
    assert _mentioned_ids(mock_bot) == set(range(1, 121))


@pytest.mark.asyncio
async def test_send_native_all_single_message_when_small(mock_bot, db_setup):
    """FR-008 / US2 сценарий 2: <= лимита -> ровно одно сообщение."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(30)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=777, chat_id=-100, topic_id=5, sender_name="Mod", text="hi"
        )

    assert mock_bot.send_message.call_count == 1
    assert _mentioned_ids(mock_bot) == set(range(1, 31))


@pytest.mark.asyncio
async def test_send_native_all_batch_flood_wait(mock_bot, db_setup):
    """FR-007: flood-wait между/на батчах соблюдается; все адресаты покрыты."""
    calls = {"n": 0}

    async def flood_first(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _retry_after(3)
        return None

    mock_bot.send_message.side_effect = flood_first

    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(60)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep, _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=777, chat_id=-100, topic_id=5, sender_name="Mod", text="hi"
        )

    # 2 батча (50+10); первый упал по flood -> повтор -> итого 3 вызова.
    assert mock_bot.send_message.call_count == 3
    assert _mentioned_ids(mock_bot) == set(range(1, 61))
    assert call(min(3, FLOOD_WAIT_CAP_SECONDS)) in mock_sleep.call_args_list


@pytest.mark.asyncio
async def test_send_native_all_no_empty_trailing_batch(mock_bot, db_setup):
    """Кратное лимиту число (100) -> ровно 2 сообщения, без пустого хвостового батча."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(100)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=777, chat_id=-100, topic_id=5, sender_name="Mod", text="hi"
        )

    assert mock_bot.send_message.call_count == 2
    assert _mentioned_ids(mock_bot) == set(range(1, 101))


@pytest.mark.asyncio
async def test_send_native_all_empty_authorized(mock_bot, db_setup):
    """FR-008 / US2 сценарий 4: пустой список -> 0 сообщений."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=[]), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=777, chat_id=-100, topic_id=5, sender_name="Mod", text="hi"
        )

    assert mock_bot.send_message.call_count == 0


def test_mention_batch_size_is_fifty():
    """Батч @all привязан к лимиту Telegram."""
    assert MENTION_BATCH_SIZE == 50


# --- US3: гейт @all (роль + кулдаун) ---

@pytest.mark.asyncio
async def test_all_mention_cooldown(mock_bot, db_setup):
    """Модератор дважды подряд: второй @all в пределах кулдауна не рассылает (FR-011)."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(3)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), _moderator():
        await NotificationService.send_native_all(
            mock_bot, sender_id=100, chat_id=-100, topic_id=5, sender_name="Mod", text="a"
        )
        after_first = mock_bot.send_message.call_count
        await NotificationService.send_native_all(
            mock_bot, sender_id=100, chat_id=-100, topic_id=5, sender_name="Mod", text="b"
        )
        after_second = mock_bot.send_message.call_count

    assert after_first == 1, "Первый @all модератора рассылается"
    assert after_second == after_first, "Повтор в пределах кулдауна не рассылает"


@pytest.mark.asyncio
async def test_all_mention_superadmin_exempt(mock_bot, db_setup):
    """Суперадмин освобождён от кулдауна: два @all подряд -> обе рассылки уходят (FR-011)."""
    import config
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(3)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock):
        await NotificationService.send_native_all(
            mock_bot, sender_id=config.ADMIN_ID, chat_id=-100, topic_id=5, sender_name="Boss", text="a"
        )
        await NotificationService.send_native_all(
            mock_bot, sender_id=config.ADMIN_ID, chat_id=-100, topic_id=5, sender_name="Boss", text="b"
        )

    assert mock_bot.send_message.call_count == 2, "Суперадмин рассылает без кулдауна"


@pytest.mark.asyncio
async def test_all_mention_non_moderator_blocked(mock_bot, db_setup):
    """Не-модератор (unit): @all не рассылается вовсе (FR-009)."""
    with patch("services.notification_service.db.get_topic_authorized_users", return_value=_authorized(3)), \
         patch("services.notification_service.asyncio.sleep", new_callable=AsyncMock), \
         patch("services.permission_service.PermissionService.is_moderator_of_topic", return_value=False):
        await NotificationService.send_native_all(
            mock_bot, sender_id=300, chat_id=-100, topic_id=5, sender_name="X", text="a"
        )

    assert mock_bot.send_message.call_count == 0


# --- US4: граница роста _alert_cache ---

@pytest.mark.asyncio
async def test_alert_cache_bounded(mock_bot, db_setup):
    """FR-012: протухшие (старше TTL) записи не накапливаются — размер кэша ограничен."""
    stale_ts = time.time() - ALERT_CACHE_TTL_SECONDS - 100
    for i in range(1500):
        NotificationService._alert_cache[(i, f"topic{i}")] = stale_ts

    await NotificationService.send_default_deny_alert(mock_bot, 999, "NewTopic")

    # 1500 протухших вычищены; осталась горстка свежих (не порядка 1500).
    assert len(NotificationService._alert_cache) <= 5
    assert len(NotificationService._alert_cache) <= ALERT_CACHE_MAX_ENTRIES


@pytest.mark.asyncio
async def test_alert_cache_dedup_preserved(mock_bot, db_setup):
    """FR-013 (guard): подавление в пределах окна и повторная отправка после окна — как прежде.
    Проходит и до, и после US4 (характеризация, format-agnostic)."""
    # В пределах окна: второй алерт по той же паре подавляется.
    await NotificationService.send_default_deny_alert(mock_bot, 1, "T")
    await NotificationService.send_default_deny_alert(mock_bot, 1, "T")
    assert mock_bot.send_message.call_count == 1, "Повтор в пределах окна подавлен"

    # За пределами окна: алерт по той же паре отправляется снова.
    NotificationService._alert_cache[(1, "T")] = time.time() - DEFAULT_DENY_WINDOW_SECONDS - 1
    await NotificationService.send_default_deny_alert(mock_bot, 1, "T")
    assert mock_bot.send_message.call_count == 2, "После окна алерт уходит снова"
