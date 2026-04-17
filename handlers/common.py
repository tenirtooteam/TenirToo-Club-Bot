# Файл: handlers/common.py
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from services.ui_service import UIService

router = Router()

@router.callback_query(F.data == "close_menu")
async def global_close_menu(callback: types.CallbackQuery, state: FSMContext):
    """Единый обработчик кнопки 'Закрыть' для всего бота."""
    await UIService.delete_msg(callback.message)
    await state.update_data(last_menu_id=None)
    await callback.answer("Закрыто")