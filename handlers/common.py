# Файл: handlers/common.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from services.ui_service import UIService
from services.permission_service import PermissionService

router = Router()

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Глобальная команда помощи, адаптирующаяся под роль пользователя."""
    user_id = message.from_user.id
    
    # Собираем текст помощи в зависимости от прав
    help_text = "🆘 <b>Справка по командам бота:</b>\n\n"
    
    help_text += "👤 <b>Основные (Для всех):</b>\n"
    help_text += "🔹 /start — Главное меню пользователя\n"
    help_text += "🔹 /help — Эта справка\n\n"
    
    if PermissionService.get_manageable_topics(user_id):
        help_text += "🛡 <b>Для модераторов:</b>\n"
        help_text += "🔹 /mod — Панель управления модерируемыми топиками (выдача доступов, управление пользователями)\n\n"
        
    if PermissionService.is_global_admin(user_id):
        help_text += "👑 <b>Для администраторов:</b>\n"
        help_text += "🔹 /admin — Панель управления ролями, группами доступа и привязкой топиков\n\n"
        
    help_text += "<i>💡 Подсказка: Бот удаляет старые меню для поддержания чистоты чата. Если меню пропало, просто введите нужную команду заново.</i>"
    
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "close_menu")
async def global_close_menu(callback: types.CallbackQuery, state: FSMContext):
    """Единый обработчик кнопки 'Закрыть' для всего бота."""
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)
    await callback.answer("Закрыто")