import logging
from aiogram import Bot
from database import db
import keyboards as kb

logger = logging.getLogger(__name__)

class EventService:
    """
    Бизнес-логика для модуля 'Мероприятия'.
    Управляет форматированием, проверкой прав и уведомлениями.
    """

    @staticmethod
    def format_event_card(event_id: int) -> str:
        """Формирует красивую карточку мероприятия."""
        event = db.get_event_details(event_id)
        if not event:
            return "❌ Мероприятие не найдено."

        status = "✅ Одобрено" if event["is_approved"] else "⏳ На модерации"
        # Batch Fetch для имен участников и лидеров [CC-7]
        participant_ids = event["participants"]
        lead_ids = event["leads"]
        all_relevant_ids = list(set(participant_ids + lead_ids + ([event["creator_id"]] if event["creator_id"] else [])))
        user_names = db.get_user_names_by_ids(all_relevant_ids)
        
        creator_name = user_names.get(event["creator_id"], "Удален")
        
        participant_names = [f"• {user_names.get(uid, f'ID:{uid}')}" for uid in participant_ids]
        lead_names = [user_names.get(uid, f"ID:{uid}") for uid in lead_ids]

        leads_str = ", ".join(lead_names) if lead_names else "Не назначен"
        participants_str = "\n".join(participant_names) if participant_names else "Пока никого нет"

        return (
            f"🏔 <b>{event['title']}</b>\n"
            f"📅 Даты: {event['start_date']} — {event['end_date'] or '?'}\n"
            f"👑 Организатор: {creator_name}\n"
            f"👨‍✈️ Ответственные: {leads_str}\n"
            f"📊 Статус: {status}\n\n"
            f"👥 Участники ({len(participant_ids)}):\n"
            f"{participants_str}"
        )

    @staticmethod
    async def notify_admins_for_approval(bot: Bot, event_id: int):
        """Отправляет карточку на модерацию всем администраторам."""
        import config
        
        # Получаем всех глобальных админов из БД
        admin_ids = set(db.get_global_admin_ids())
        # Обязательно добавляем системного админа из конфига
        admin_ids.add(config.ADMIN_ID)
        
        card_text = f"🚨 <b>Новое Мероприятие на модерацию!</b>\n\n" + EventService.format_event_card(event_id)
        kb_markup = kb.get_event_moderation_kb(event_id)
        
        for adm_id in admin_ids:
            try:
                await bot.send_message(adm_id, card_text, reply_markup=kb_markup, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу {adm_id}: {e}")

    @staticmethod
    def can_edit_event(user_id: int, event_id: int) -> bool:
        """
        [Admin Override]
        Проверяет, может ли пользователь редактировать мероприятие.
        Разрешено:
        1. Автору мероприятия.
        2. Любому глобальному администратору.
        """
        if db.is_global_admin(user_id):
            return True
            
        event = db.get_event_details(event_id)
        if not event:
            return False
            
        return event["creator_id"] == user_id
