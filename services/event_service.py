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

        from services.date_service import DateService
        
        # Динамически добавляем дни недели для красоты UI [CC-2]
        d_start = event['start_date']
        if event['start_iso']:
            d_start += DateService.get_weekday_suffix(event['start_iso'])
            
        d_end = event['end_date']
        if d_end and event['end_iso']:
            d_end += DateService.get_weekday_suffix(event['end_iso'])
        elif not d_end:
            d_end = "?"

        return (
            f"🏔 <b>{event['title']}</b>\n"
            f"📅 Даты: {d_start} — {d_end}\n"
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
        
        # Получаем всех глобальных админов из БД и гарантируем тип int [PL-HI]
        admin_ids = set(int(uid) for uid in db.get_global_admin_ids())
        # Обязательно добавляем системного админа из конфига (кастуем для верности)
        admin_ids.add(int(config.ADMIN_ID))
        
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

    @staticmethod
    def get_active_events() -> list:
        """Возвращает список активных мероприятий."""
        return db.get_active_events()

    @staticmethod
    def get_pending_events() -> list:
        """Возвращает список мероприятий на модерации."""
        return db.get_pending_events()

    @staticmethod
    def get_event_details(event_id: int) -> dict:
        """Возвращает полную информацию о мероприятии."""
        return db.get_event_details(event_id)

    @staticmethod
    def is_event_participant(event_id: int, user_id: int) -> bool:
        """Проверяет, участвует ли пользователь в мероприятии."""
        return db.is_event_participant(event_id, user_id)

    @staticmethod
    async def notify_admins_of_participation_request(bot: Bot, event_id: int, user_id: int):
        """
        Отправляет уведомление о новой заявке на участие админам и организатору. [PL-5.1.13]
        """
        import config
        from database.db import get_user_name
        
        event = db.get_event_details(event_id)
        if not event:
            return
            
        user_name = get_user_name(user_id) or f"ID:{user_id}"
        
        # Получатели: все админы + создатель мероприятия
        admin_ids = set(int(uid) for uid in db.get_global_admin_ids())
        admin_ids.add(int(config.ADMIN_ID))
        if event["creator_id"]:
            admin_ids.add(int(event["creator_id"]))
            
        text = (
            f"🔔 <b>Новая заявка на участие!</b>\n\n"
            f"👤 Пользователь: <b>{user_name}</b>\n"
            f"🏔 Мероприятие: <b>{event['title']}</b>\n\n"
            f"Рассмотрите заявку в разделе 'Аудит'."
        )
        
        for adm_id in admin_ids:
            try:
                await bot.send_message(adm_id, text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление о записи админу {adm_id}: {e}")

    @staticmethod
    async def notify_organizers_of_direct_join(bot: Bot, event_id: int, user_id: int):
        """
        Отправляет уведомление о прямой записи (без аудита) админам и организатору. [PL-5.1.13]
        """
        import config
        from database.db import get_user_name
        
        event = db.get_event_details(event_id)
        if not event: return
        
        user_name = get_user_name(user_id) or f"ID:{user_id}"
        
        admin_ids = set(int(uid) for uid in db.get_global_admin_ids())
        admin_ids.add(int(config.ADMIN_ID))
        if event["creator_id"]:
            admin_ids.add(int(event["creator_id"]))
            
        text = (
            f"✅ <b>Новый участник!</b>\n\n"
            f"👤 Пользователь: <b>{user_name}</b>\n"
            f"🏔 Мероприятие: <b>{event['title']}</b>\n\n"
            f"Запись прошла автоматически через анонс."
        )
        
        for adm_id in admin_ids:
            try:
                await bot.send_message(adm_id, text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление о вступлении админу {adm_id}: {e}")
