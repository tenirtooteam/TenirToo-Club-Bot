# Файл: services/notification_service.py
import time
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

logger = logging.getLogger(__name__)


class NotificationService:
    _alert_cache = {}

    @classmethod
    async def send_default_deny_alert(cls, bot: Bot, user_id: int, topic_name: str):
        """
        Sends a rate-limited PM alert to an administrator when their message is deleted
        due to Default Deny mode.
        """
        now = time.time()
        cache_key = (user_id, topic_name)
        last_sent = cls._alert_cache.get(cache_key, 0)

        if now - last_sent < 60:
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
        cache_key = (user_id, f"member_{topic_name}")
        last_sent = cls._alert_cache.get(cache_key, 0)

        # 1-hour rate limit to avoid PM spamming
        if now - last_sent < 3600:
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
    @staticmethod
    async def send_native_all(bot: Bot, chat_id: int, topic_id: int, sender_name: str, text: str):
        """
        Отправляет сообщение с невидимыми упоминаниями всех авторизованных участников.
        Использует список (id, first_name, last_name).
        """
        authorized_users = db.get_topic_authorized_users(topic_id)

        if not authorized_users:
            logger.info(f"🔔 Оповещение @all: список пользователей для топика {topic_id} пуст.")
            return

        # Лимит Telegram на упоминания в одном сообщении ~50 человек.
        # Формируем скрытые ссылки через символ нулевой ширины.
        mentions = ""
        for user_data in authorized_users[:50]:
            user_id = user_data[0]
            # Скрытая ссылка для вызова пуш-уведомления
            mentions += f'<a href="tg://user?id={user_id}">&#8203;</a>'

        full_text = (
            f"📢 <b>{sender_name}</b>:\n"
            f"{text}\n"
            f"{mentions}"
        )

        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=topic_id if topic_id != -1 else None,
                text=full_text,
                parse_mode="HTML"
            )
            logger.info(f"✅ Нативное оповещение отправлено в топик {topic_id} ({len(authorized_users[:50])} чел.)")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при отправке @all: {e}")

    @staticmethod
    async def send_to_users(bot: Bot, user_ids: list[int], text: str, reply_markup=None):
        """
        Отправляет личное сообщение списку пользователей.
        Используется для уведомлений о результатах аудита и т.д.
        """
        for u_id in set(user_ids):
            try:
                await bot.send_message(
                    chat_id=u_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                logger.info(f"✉️ Уведомление отправлено пользователю {u_id}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить уведомление {u_id}: {e}")
