# Файл: handlers/common.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import math
from database import db
import keyboards as kb
from services.callback_guard import safe_callback
from services.permission_service import PermissionService
from services.ui_service import UIService

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



@router.callback_query(F.data.startswith("usr_pg_"))
@safe_callback()
async def process_user_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Глобальный пагинатор поиска пользователей."""
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    query = data.get("disambig_query", "")
    
    if not query:
        await callback.answer("Сессия истекла.", show_alert=True)
        return
        
    results = db.find_users_by_query(query)
    total_pages = math.ceil(len(results) / 7)
    start_idx = (page - 1) * 7
    markup = kb.user_disambiguation_kb(results[start_idx:start_idx + 7], page, total_pages)
    await callback.message.edit_reply_markup(reply_markup=markup)

@router.callback_query(F.data.startswith("usr_pick_"))
@safe_callback()
async def process_user_pick(callback: types.CallbackQuery, state: FSMContext):
    """Глобальный обработчик выбора найденного пользователя."""
    target_user_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    action = data.get("disambig_action")
    context_id = data.get("disambig_context")
    
    user_name = db.get_user_name(target_user_id)
    
    if action == "dir_add":
        db.grant_direct_access(target_user_id, context_id)
        await callback.message.edit_text(f"✅ Прямой доступ выдан пользователю: {user_name}")
    elif action == "mod_add":
        role_id = db.get_role_id("moderator")
        if role_id != 0:
            db.grant_role(target_user_id, role_id, context_id)
            await callback.message.edit_text(f"✅ {user_name} назначен модератором.")
        else:
            await callback.message.edit_text("❌ Ошибка роли.")
    elif action == "admin_role_target":
        await state.set_state(None)
        await callback.message.edit_text(
            f"Пользователь {user_name} выбран. Выберите роль:",
            reply_markup=kb.role_selection_kb(target_user_id)
        )
        
        
    # Сбрасываем стейт
    await state.update_data(disambig_query=None, disambig_action=None, disambig_context=None, disambig_role_id=None)

@router.callback_query(F.data == "close_menu")
async def global_close_menu(callback: types.CallbackQuery, state: FSMContext):
    """Единый обработчик кнопки 'Закрыть' для всего бота."""
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)
    await callback.answer("Закрыто")