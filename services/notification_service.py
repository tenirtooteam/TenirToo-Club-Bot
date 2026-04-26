# Файл: services/notification_service.py
import logging
from aiogram import Bot
from database import db

logger = logging.getLogger(__name__)


class NotificationService:
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