# Файл: services/notification_service.py
import time
import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)

# --- Broadcast tuning constants (feature 013, FR-015) ---
# Пауза между последовательными отправками/батчами — кооперативная, не блокирует loop (R-DATA-7).
BROADCAST_PACING_SECONDS = 0.05
# Потолок ожидания по flood-wait: защита от битого/абсурдного retry_after (не залипаем на минуты).
FLOOD_WAIT_CAP_SECONDS = 30
# Сколько раз повторить отправку одному адресату после flood-wait, прежде чем признать недоставку.
FLOOD_WAIT_MAX_RETRIES = 1
# Лимит Telegram на упоминания в одном сообщении — размер батча @all.
MENTION_BATCH_SIZE = 50
# Минимальный интервал между успешными @all одного отправителя-модератора (анти-абьюз).
ALL_MENTION_COOLDOWN_SECONDS = 60
# Окна подавления повторных PM-алертов модерации (наблюдаемое поведение неизменно, FR-013).
DEFAULT_DENY_WINDOW_SECONDS = 60
MEMBER_DENY_WINDOW_SECONDS = 3600
# Ограничение роста кэша алертов (FR-012): порог очистки протухших записей и жёсткий потолок размера.
ALERT_CACHE_TTL_SECONDS = 3600
ALERT_CACHE_MAX_ENTRIES = 1000


def reset_notification_state() -> None:
    """Сбрасывает классовое состояние рассылок между тестами (R-TEST-1)."""
    NotificationService._alert_cache.clear()
    NotificationService._all_cooldown.clear()


class NotificationService:
    _alert_cache = {}
    # sender_id -> timestamp последнего успешного @all (анти-абьюз, в памяти процесса).
    _all_cooldown: dict[int, float] = {}

    @staticmethod
    async def _send_message_resilient(bot: Bot, **send_kwargs) -> bool:
        """
        Одиночная отправка с обработкой flood-wait (feature 013, contract C-4).

        При `TelegramRetryAfter` (429) — ждём min(retry_after, cap) и повторяем до
        FLOOD_WAIT_MAX_RETRIES раз. Прочие `TelegramAPIError` (заблокировал бота и т.п.) — логируем и
        возвращаем False, НЕ поднимая исключение: рассылка продолжается для остальных (FR-003).
        Возвращает True при доставке, False при финальном отказе.
        """
        chat_id = send_kwargs.get("chat_id")
        for attempt in range(FLOOD_WAIT_MAX_RETRIES + 1):
            try:
                await bot.send_message(**send_kwargs)
                return True
            except TelegramRetryAfter as e:
                # Порядок except важен: TelegramRetryAfter — подкласс TelegramAPIError.
                if attempt >= FLOOD_WAIT_MAX_RETRIES:
                    logger.warning(
                        f"⚠️ Flood-wait не исчерпан за {FLOOD_WAIT_MAX_RETRIES} повтор(ов) "
                        f"для {chat_id}: адресат пропущен."
                    )
                    return False
                wait = min(e.retry_after, FLOOD_WAIT_CAP_SECONDS)
                logger.info(f"⏳ Flood-wait {wait}s перед повтором отправки для {chat_id}")
                await asyncio.sleep(wait)
            except TelegramAPIError as e:
                logger.warning(f"⚠️ Не удалось отправить {chat_id}: {e}")
                return False
        return False

    @classmethod
    def _prune_alert_cache(cls, now: float) -> None:
        """
        Ограничивает рост _alert_cache (feature 013, FR-012): удаляет записи, чьё окно защиты от
        повторов заведомо истекло (старше ALERT_CACHE_TTL_SECONDS), и как страховка держит размер
        под ALERT_CACHE_MAX_ENTRIES, вытесняя самые старые. Наблюдаемую дедуп-логику не меняет:
        протухшая запись всё равно была бы отправлена заново (FR-013).
        """
        cache = cls._alert_cache
        expired = [k for k, ts in cache.items() if now - ts > ALERT_CACHE_TTL_SECONDS]
        for k in expired:
            del cache[k]
        overflow = len(cache) - ALERT_CACHE_MAX_ENTRIES
        if overflow > 0:
            for k, _ in sorted(cache.items(), key=lambda kv: kv[1])[:overflow]:
                del cache[k]

    @classmethod
    async def send_default_deny_alert(cls, bot: Bot, user_id: int, topic_name: str):
        """
        Sends a rate-limited PM alert to an administrator when their message is deleted
        due to Default Deny mode.
        """
        now = time.time()
        cls._prune_alert_cache(now)
        cache_key = (user_id, topic_name)
        last_sent = cls._alert_cache.get(cache_key, 0)

        if now - last_sent < DEFAULT_DENY_WINDOW_SECONDS:
            logger.info(f"🔇 Default Deny PM alert rate-limited for admin {user_id} in {topic_name}")
            return

        cls._alert_cache[cache_key] = now

        text = (
            f"🏔 <b>Доступ ограничен (Default Deny)</b>\n\n"
            f"Топик <b>«{topic_name}»</b> находится в режиме закрытого доступа по умолчанию. "
            f"Ваше сообщение было удалено.\n\n"
            f"Настройте права доступа в панели управления или свяжитесь с создателем."
        )

        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настроить доступ", callback_data="all_topics_list")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
        ])

        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.info(f"✉️ Отправлен PM-алерт Default Deny администратору {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить PM-алерт Default Deny администратору {user_id}: {e}")

    @classmethod
    async def send_member_deny_alert(cls, bot: Bot, user_id: int, topic_name: str):
        """
        Sends a rate-limited (1 hour) soft PM alert to a member when their message
        is stealth-deleted in a restricted topic.
        """
        now = time.time()
        cls._prune_alert_cache(now)
        cache_key = (user_id, f"member_{topic_name}")
        last_sent = cls._alert_cache.get(cache_key, 0)

        # 1-hour rate limit to avoid PM spamming
        if now - last_sent < MEMBER_DENY_WINDOW_SECONDS:
            return

        cls._alert_cache[cache_key] = now

        text = (
            f"📍 <b>Доступ ограничен</b>\n\n"
            f"Топик <b>«{topic_name}»</b> находится в закрытом режиме. "
            f"Ваше сообщение было удалено.\n\n"
            f"Доступ в эту локацию предоставляется только организаторам или участникам по спискам."
        )

        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML"
            )
            logger.info(f"✉️ Отправлен PM-алерт о модерации участнику {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить PM-алерт о модерации участнику {user_id}: {e}")
    @classmethod
    async def send_native_all(
        cls, bot: Bot, sender_id: int, chat_id: int, topic_id: int, sender_name: str, text: str
    ):
        """
        Отправляет @all-оповещение со скрытыми упоминаниями ВСЕХ авторизованных участников топика
        (feature 013, FR-005..008). Список режется на батчи по MENTION_BATCH_SIZE (лимит упоминаний
        Telegram на сообщение) — тихого среза до 50 больше нет; между батчами — кооперативная пауза,
        каждый батч уходит через flood-wait-устойчивый helper.

        `sender_id` — отправитель @all. Гейт (feature 013, FR-009..011): рассылка разрешена только
        модератору топика или суперадмину; для модератора — не чаще ALL_MENTION_COOLDOWN_SECONDS;
        суперадмин от кулдауна освобождён. Отказ тихий — вызывающий хендлер уже удалил триггер.
        """
        is_super = PermissionService.is_superadmin(sender_id)
        if not (is_super or PermissionService.is_moderator_of_topic(sender_id, topic_id)):
            logger.info(f"🚫 @all от {sender_id} в топике {topic_id} отклонён: нет прав модератора.")
            return

        now = time.time()
        if not is_super and now - cls._all_cooldown.get(sender_id, 0) < ALL_MENTION_COOLDOWN_SECONDS:
            logger.info(f"🔇 @all от {sender_id} отклонён: rate-limit ({ALL_MENTION_COOLDOWN_SECONDS}s).")
            return

        authorized_users = db.get_topic_authorized_users(topic_id)

        if not authorized_users:
            logger.info(f"🔔 Оповещение @all: список пользователей для топика {topic_id} пуст.")
            return

        thread_id = topic_id if topic_id != -1 else None
        total = len(authorized_users)
        batches = (total + MENTION_BATCH_SIZE - 1) // MENTION_BATCH_SIZE
        sent = 0

        for start in range(0, total, MENTION_BATCH_SIZE):
            batch = authorized_users[start:start + MENTION_BATCH_SIZE]
            # Скрытые ссылки (символ нулевой ширины) — пуш без видимого текста упоминания.
            mentions = "".join(f'<a href="tg://user?id={u[0]}">&#8203;</a>' for u in batch)
            full_text = f"📢 <b>{sender_name}</b>:\n{text}\n{mentions}"

            if start > 0:
                await asyncio.sleep(BROADCAST_PACING_SECONDS)

            delivered = await cls._send_message_resilient(
                bot,
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=full_text,
                parse_mode="HTML",
            )
            if delivered:
                sent += len(batch)

        # Кулдаун потребляется только реальной рассылкой модератора (суперадмин — без записи).
        if not is_super and sent > 0:
            cls._all_cooldown[sender_id] = now

        logger.info(
            f"✅ @all в топик {topic_id}: охвачено {sent}/{total} чел. в {batches} сообщ."
        )

    @classmethod
    async def send_to_users(cls, bot: Bot, user_ids: list[int], text: str, reply_markup=None):
        """
        Отправляет личное сообщение списку пользователей (feature 013, FR-001..004).
        Каждая отправка идёт через flood-wait-устойчивый helper, между отправками — кооперативная
        пауза; недоступный адресат не прерывает рассылку. Дедуп по set() с int-кастом (R-DATA-9).
        Используется для уведомлений о результатах аудита и т.д.
        """
        recipients = {int(u) for u in user_ids}
        for i, u_id in enumerate(recipients):
            if i > 0:
                await asyncio.sleep(BROADCAST_PACING_SECONDS)
            delivered = await cls._send_message_resilient(
                bot,
                chat_id=u_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            if delivered:
                logger.info(f"✉️ Уведомление отправлено пользователю {u_id}")
