# Файл: services/ui_service.py
import logging
from functools import wraps
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class UIService:
    # Команды, которые поддерживают пагинацию (принимают аргумент page)
    PAGINATED_CMDS = {"manage_groups", "manage_users", "all_topics_list", "list_users_roles"}

    @staticmethod
    async def clear_last_menu(state: FSMContext, bot: Bot, chat_id: int):
        """Удаляет все запомненные системные сообщения из чата."""
        data = await state.get_data()
        last_ids = data.get("last_menu_ids", [])
        
        # Поддержка старого формата (если остался в FSM)
        old_id = data.get("last_menu_id")
        if old_id: last_ids.append(old_id)

        for msg_id in last_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                logger.info(f"🧹 Удалено сообщение: {msg_id}")
            except Exception:
                pass
        
        await state.update_data(last_menu_ids=[], last_menu_id=None)

    @staticmethod
    async def delete_msg(message: types.Message):
        """Безопасное удаление одного сообщения пользователя."""
        try:
            await message.delete()
        except Exception:
            pass

    @staticmethod
    async def finish_input(state: FSMContext, message: types.Message, reset_state: bool = True):
        """
        Единый метод завершения FSM-ввода:
        удаляет старое меню/промпт, удаляет сообщение пользователя,
        опционально сбрасывает состояние ввода (по умолчанию Да).
        """
        await UIService.clear_last_menu(state, message.bot, message.chat.id)
        await UIService.delete_msg(message)
        if reset_state:
            await state.set_state(None)

    @staticmethod
    async def send_redirected_menu(
        message: types.Message,
        state: FSMContext,
        text: str,
        reply_markup: types.InlineKeyboardMarkup = None,
        error_prefix: str = "меню"
    ):
        """
        Реализует протокол «Стерильного интерфейса» для команд:
        перенос в ЛС из групп с очисткой триггеров.
        """
        user_id = message.from_user.id

        if message.chat.type != "private" and error_prefix is not None:
            try:
                sent_message = await message.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                await state.update_data(last_menu_ids=[sent_message.message_id])
                await UIService.delete_msg(message)
                return sent_message
            except Exception:
                error_msg = (
                    f"⚠️ <b>{message.from_user.first_name}</b>, я не могу отправить вам {error_prefix} в ЛС.\n"
                    f"Пожалуйста, сначала напишите мне в личные сообщения (нажмите /start)."
                )
                sent_error = await message.answer(error_msg, parse_mode="HTML")
                await state.update_data(last_menu_ids=[sent_error.message_id])
                await UIService.delete_msg(message)
                return sent_error
        else:
            # Если уже в личке или редирект не требуется. 
            # Не сбрасываем состояние, так как это может быть промежуточный шаг.
            await UIService.finish_input(state, message, reset_state=False)
            sent_message = await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            await state.update_data(last_menu_ids=[sent_message.message_id])
            return sent_message

    @staticmethod
    async def show_temp_message(state: FSMContext, event: types.Message | types.CallbackQuery, text: str, reply_markup=None):
        """Отображает временное сообщение БЕЗ удаления предыдущего (добавляет в стек)."""
        bot = event.bot if isinstance(event, types.Message) else event.message.bot
        chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id
        
        if isinstance(event, types.Message):
            await UIService.delete_msg(event)
            
        msg_source = event if isinstance(event, types.Message) else event.message
        sent = await msg_source.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        
        # Добавляем в список для последующей зачистки
        data = await state.get_data()
        last_ids = data.get("last_menu_ids", [])
        last_ids.append(sent.message_id)
        await state.update_data(last_menu_ids=last_ids)
        return sent

    @staticmethod
    async def show_menu(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        text: str,
        reply_markup: types.InlineKeyboardMarkup = None,
        parse_mode: str = "HTML"
    ):
        """
        Универсальный метод отображения/обновления меню.
        Соблюдает Sterile UI Protocol:
        - Если CallbackQuery — редактирует текущее сообщение.
        - Если Message — чистит чат и шлет новое.
        - Всегда гарантирует актуальность last_menu_id.
        """
        is_cb = isinstance(event, types.CallbackQuery)

        if is_cb:
            try:
                await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception:
                # Fallback: сообщение нельзя редактировать (слишком старое или контент идентичен).
                # Отправляем новое и удаляем старое.
                new_msg = await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                await UIService.delete_msg(event.message)
                await state.update_data(last_menu_ids=[new_msg.message_id])
            # answer() вызывается ровно один раз, в конце, вне зависимости от пути выполнения
            try:
                await event.answer()
            except Exception:
                pass
        else:
            # Если это сообщение (текстовый ввод), чистим чат, но СОХРАНЯЕМ состояние
            await UIService.finish_input(state, event, reset_state=False)
            new_msg = await event.bot.send_message(
                event.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            await state.update_data(last_menu_ids=[new_msg.message_id])

    @staticmethod
    async def ask_input(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        text: str,
        state_to_set=None
    ):
        """
        Удаляет текущее меню, отправляет промпт и ставит его на слежение (last_menu_id).
        """
        bot = event.bot if isinstance(event, types.Message) else event.message.bot
        chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id

        await UIService.clear_last_menu(state, bot, chat_id)

        if isinstance(event, types.Message):
            await UIService.delete_msg(event)

        msg_source = event if isinstance(event, types.Message) else event.message
        sent = await msg_source.answer(text, parse_mode="HTML")

        await state.update_data(last_menu_ids=[sent.message_id])
        if state_to_set:
            await state.set_state(state_to_set)
        return sent
    @staticmethod
    async def generic_navigator(state: FSMContext, event: types.Message | types.CallbackQuery, callback_data: str):
        """Ультимативный роутер: callback_data -> UI экран."""
        from database import db
        import keyboards as kb
        from services.permission_service import PermissionService
        
        user_id = event.from_user.id
        
        # 1. Глобальная навигация (Simple)
        simple = {
            "admin_main": ("🛠 <b>Панель управления</b>", kb.main_admin_kb),
            "user_main": ("Главное меню участника:", kb.user_main_kb),
            "user_profile_view": (None, None), # Специальная обработка ниже
            "user_topics": ("📍 <b>Топики, в которых ты можешь писать:</b>", lambda: kb.user_topics_list_kb(user_id)),
            "manage_groups": ("📂 <b>Группы доступа:</b>", kb.groups_list_kb),
            "manage_users": ("👥 <b>Список пользователей:</b>", kb.users_list_kb),
            "all_topics_list": ("📍 <b>Все топики:</b>", kb.all_topics_kb),
            "roles_dashboard": ("🛡 <b>Центр ролей</b>", lambda: kb.roles_dashboard_kb(PermissionService.is_global_admin(user_id))),
            "roles_faq": ("🛡 <b>Описание ролей</b>\n\n👑 <b>Админ</b>: Полный доступ к управлению группами, топиками и пользователями.\n🛡 <b>Модератор</b>: Управление доступом и модераторами в рамках конкретного топика.\n💎 <b>Суперадмин</b>: Системный владелец с неограниченными правами.", kb.back_to_roles_dashboard_kb),
            "list_users_roles": ("📋 <b>Пользователи с ролями:</b>", kb.users_list_kb), # Можно заменить на спец. клавиатуру позже
            "moderator": ("🛠 <b>Панель модератора</b>\nВыберите топик:", lambda: kb.moderator_topics_list_kb(PermissionService.get_manageable_topics(user_id))),
            "templates_faq": (None, None), # Redirects to help_service logic
        }
        
        cmd = callback_data.split("_pg_")[0]
        page = int(callback_data.split("_pg_")[1]) if "_pg_" in callback_data else 1
        if cmd in simple:
            text, kb_func = simple[cmd]
            
            # 1.1 Специальные редиректы
            if cmd == "templates_faq":
                return await UIService.generic_navigator(state, event, f"help:templates:manage_groups")
            
            if cmd == "user_profile_view":
                # Переходим к блоку "Инфо-карточки" ниже
                pass
            elif kb_func is not None:
                if cmd in UIService.PAGINATED_CMDS:
                    markup = kb_func(page=page)
                else:
                    markup = kb_func()
                return await UIService.show_menu(state, event, text, reply_markup=markup)

        # 1.5 Специальная обработка HELP (help:{key}:{back_data})
        if cmd.startswith("help:"):
            from handlers.common import show_help_view
            parts = cmd.split(":")
            return await show_help_view(state, event, key=parts[1], back_data=parts[2] if len(parts) > 2 else "admin_main")

        # 2. Параметризованная навигация
        p = callback_data.split("_")
        
        # Инфо-карточки
        if cmd == "user_profile_view":
            user_name = db.get_user_name(user_id)
            user_templates = db.get_user_group_templates(user_id)
            groups_str = ", ".join(g[1] for g in user_templates) if user_templates else "нет назначенных шаблонов"
            roles = list(db.get_user_roles(user_id))
            available_topics = db.get_user_available_topics(user_id)
            text = UIService.format_user_card(user_id, user_name, groups_str, roles, available_topics)
            return await UIService.show_menu(state, event, text, reply_markup=kb.user_profile_kb())

        if "user_info" in cmd: return await UIService.show_user_detail(state, event, int(p[-1]))
        if "group_info" in cmd: return await UIService.show_group_detail(state, event, int(p[-1]))
        if "topic_" in cmd and ("global" in cmd or "in_group" in cmd):
            return await UIService.show_topic_detail(state, event, int(p[-1]), int(p[-2]) if "in_group" in cmd else 0)

        if cmd.startswith("u_topic_info"):
            t_id = int(p[-1])
            t_name = db.get_topic_name(t_id)
            access_groups = db.get_groups_by_topic(t_id)
            groups_str = "\n".join(f"— {g}" for g in access_groups) if access_groups else "Доступ не настроен"
            has_access = db.can_write(user_id, t_id)
            access_status = "✅ У тебя есть доступ." if has_access else "❌ У тебя нет доступа."
            text = (
                f"📍 <b>Информация о топике</b>\n\n"
                f"<b>Название:</b> {t_name}\n"
                f"<b>ID:</b> <code>{t_id}</code>\n\n"
                f"👥 <b>Связанные шаблоны:</b>\n{groups_str}\n\n"
                f"🔐 <b>Твой статус:</b> {access_status}\n\n"
                f"<i>Если доступа нет, твои сообщения в этом топике будут удаляться автоматически.</i>"
            )
            return await UIService.show_menu(state, event, text, reply_markup=kb.user_topic_detail_kb())

        # Модерация топиков
        if cmd.startswith("mod_topic_select") or cmd.startswith("mod_back_to_topic"):
            t_id = int(p[-1])
            return await UIService.show_menu(state, event, f"📍 <b>Управление: {db.get_topic_name(t_id)}</b>", kb.moderator_topic_menu_kb(t_id))
        
        if cmd.startswith("mod_topic_groups"):
            t_id = int(p[-1])
            return await UIService.show_menu(state, event, f"📂 <b>Группы топика: {db.get_topic_name(t_id)}</b>", kb.moderator_group_list_kb(t_id, page=page))
            
        if cmd.startswith("mod_topic_moderators"):
            t_id = int(p[-1])
            return await UIService.show_menu(state, event, f"👑 <b>Модераторы: {db.get_topic_name(t_id)}</b>", kb.moderator_topic_moderators_kb(t_id))
            
        if cmd.startswith("mod_gr_addlist"):
            t_id = int(p[-1])
            return await UIService.show_menu(state, event, "🔗 <b>Привязка группы:</b>", kb.moderator_available_groups_kb(t_id, page=page))
            
        if cmd.startswith("mod_users_manage"):
            t_id = int(p[-1])
            return await UIService.show_menu(state, event, f"👥 <b>Юзеры топика: {db.get_topic_name(t_id)}</b>", kb.moderator_users_list_kb(t_id, page=page))

        # Админка: управление ролями и правами
        if cmd.startswith("user_roles_manage"):
            u_id = int(p[-1])
            return await UIService.show_menu(state, event, f"🛡 <b>Роли пользователя: {db.get_user_name(u_id)}</b>", kb.user_roles_manage_kb(u_id))
            
        if cmd.startswith("user_templates_manage"):
            u_id = int(p[3])
            return await UIService.show_menu(state, event, f"🔐 <b>Шаблоны пользователя: {db.get_user_name(u_id)}</b>", kb.user_groups_edit_kb(u_id, page=page))

        if cmd.startswith("tmpl_act_start_"):
            action = p[3]
            g_id = int(p[4])
            title = "⚡ Выберите топик для ПРИМЕНЕНИЯ шаблона:" if action == "apply" else "🔄 Выберите топик для СИНХРОНИЗАЦИИ с шаблоном:"
            return await UIService.show_menu(state, event, title, reply_markup=kb.template_action_topic_select_kb(g_id, action, page=page))
            
        if cmd.startswith("group_topics_list"):
            g_id = int(p[-1])
            return await UIService.show_menu(state, event, f"📍 <b>Топики группы: {db.get_group_name(g_id)}</b>", kb.group_topics_list_kb(g_id, page=page))
            
        if cmd.startswith("topic_assign_pg"):
            u_id = int(p[-1])
            return await UIService.show_menu(state, event, f"📍 <b>Выбор топика для: {db.get_user_name(u_id)}</b>", kb.topic_selection_for_role_kb(u_id, page=page))

        # Резервный лог и сброс на главное меню (если что-то пошло не так)
        logger.warning(f"⚠️ [NAVIGATOR] Неизвестная команда или некорректные данные: {cmd} (data: {callback_data})")
        await UIService.show_admin_dashboard(state, event, text="⚠️ Ошибка навигации. Возврат в главное меню:")

    @staticmethod
    async def show_admin_dashboard(state: FSMContext, event: types.Message | types.CallbackQuery, text: str = "🛠 <b>Панель управления</b>"):
        """Отображает главную панель администратора."""
        from services.permission_service import PermissionService
        import keyboards as kb
        
        await UIService.show_menu(state, event, text, reply_markup=kb.main_admin_kb())

    @staticmethod
    async def show_user_detail(state: FSMContext, event: types.Message | types.CallbackQuery, user_id: int):
        """Отображает детальную карточку пользователя."""
        from database import db
        from services.permission_service import PermissionService
        import keyboards as kb

        user_name = db.get_user_name(user_id)
        user_templates = db.get_user_group_templates(user_id)
        groups_str = ", ".join(g[1] for g in user_templates) if user_templates else "нет назначенных шаблонов"
        roles = db.get_user_roles(user_id)
        topics = db.get_user_available_topics(user_id)
        
        text = UIService.format_user_card(user_id, user_name, groups_str, roles, topics)
        
        is_sa = PermissionService.is_superadmin(event.from_user.id)
        
        await UIService.show_menu(state, event, text, reply_markup=kb.user_edit_kb(user_id, is_superadmin=is_sa))

    @staticmethod
    async def show_group_detail(state: FSMContext, event: types.Message | types.CallbackQuery, group_id: int):
        """Отображает информацию о группе."""
        from database import db
        import keyboards as kb
        
        g_name = db.get_group_name(group_id)
        topics_count = len(db.get_topics_of_group(group_id))
        text = f"📂 <b>Группа:</b> {g_name}\n📍 <b>Топиков:</b> {topics_count}"
        await UIService.show_menu(state, event, text, reply_markup=kb.group_edit_kb(group_id))

    @staticmethod
    async def show_topic_detail(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int, group_id: int = 0):
        """Отображает информацию о топике."""
        from database import db
        import keyboards as kb
        
        t_name = db.get_topic_name(topic_id)
        access_groups = db.get_groups_by_topic(topic_id)
        groups_str = ", ".join(access_groups) if access_groups else "НЕТ ДОСТУПА"
        text = (
            f"📍 <b>Информация о топике</b>\n\n"
            f"<b>Наименование:</b> {t_name}\n"
            f"<b>ID:</b> <code>{topic_id}</code>\n"
            f"<b>Доступ имеют:</b> {groups_str}"
        )
        await UIService.show_menu(state, event, text, reply_markup=kb.topic_edit_kb(topic_id, group_id=group_id))

    @staticmethod
    async def show_moderator_groups(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int, page: int = 1):
        """Отображает список групп для модератора топика."""
        from database import db
        import keyboards as kb
        t_name = db.get_topic_name(topic_id)
        text = f"📂 <b>Группы доступа для топика {t_name}</b>"
        await UIService.show_menu(state, event, text, reply_markup=kb.moderator_group_list_kb(topic_id, page=page))

    @staticmethod
    async def show_moderator_moderators(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int):
        """Отображает список модераторов топика."""
        from database import db
        import keyboards as kb
        t_name = db.get_topic_name(topic_id)
        text = f"👑 <b>Модераторы топика {t_name}</b>"
        await UIService.show_menu(state, event, text, reply_markup=kb.moderator_topic_moderators_kb(topic_id))

    @staticmethod
    async def show_moderator_dashboard(state: FSMContext, event: types.Message | types.CallbackQuery):
        """Отображает главную панель модератора."""
        return await UIService.generic_navigator(state, event, "moderator")

    @staticmethod
    def get_confirmation_ui(action: str, target_id: int, extra_id: int = 0) -> tuple[str, str]:
        """
        Возвращает (текст_подтверждения, колбэк_для_отмены).
        Используется для построения экрана подтверждения.
        """
        from services.management_service import ManagementService
        from database import db
        
        # Логика текстов и навигации
        if action == "group_del":
            name = ManagementService.get_entity_name("group", target_id)
            return (
                f"⚠️ <b>ВНИМАНИЕ!</b>\n\nВы действительно хотите удалить группу <b>{name}</b>?\n<i>Это действие нельзя отменить!</i>",
                f"group_info_{target_id}"
            )
        elif action == "topic_del" or action == "mod_topic_del":
            name = ManagementService.get_entity_name("topic", target_id)
            g_name = ManagementService.get_entity_name("group", extra_id)
            back = f"topic_in_group_{target_id}_{extra_id}" if action == "topic_del" else f"mod_topic_groups_{target_id}"
            return (f"❓ Убрать топик <b>{name}</b> из группы <b>{g_name}</b>?", back)
            
        elif action == "global_topic_del":
            name = ManagementService.get_entity_name("topic", target_id)
            return (
                f"⚠️ <b>КРИТИЧЕСКОЕ ДЕЙСТВИЕ!</b>\n\nУдалить топик <b>{name}</b> из БД?\n<i>Это очистит все привязки и роли!</i>",
                f"topic_global_view_{target_id}"
            )
        elif action == "user_del":
            name = ManagementService.get_entity_name("user", target_id)
            return (
                f"⚠️ <b>ВНИМАНИЕ!</b>\n\nУдалить пользователя <b>{name}</b> (ID: {target_id})?\n<i>Это аннулирует все его доступы!</i>",
                f"user_info_{target_id}"
            )
        elif action.startswith("role_rev"):
            name = ManagementService.get_entity_name("user", target_id)
            role_id = int(action.split("_")[-1]) if action != "role_rev" else 0
            role_name = db.get_role_name_by_id(role_id) if role_id else "роль"
            context = f"топика {db.get_topic_name(extra_id)}" if extra_id else "глобально"
            return (
                f"❓ Отозвать роль <b>{role_name}</b> у пользователя <b>{name}</b> ({context})?",
                f"user_roles_manage_{target_id}"
            )
        elif action == "mod_rem":
            name = ManagementService.get_entity_name("user", target_id)
            t_name = ManagementService.get_entity_name("topic", extra_id)
            return (
                f"❓ Снять права модератора с <b>{name}</b> в топике <b>{t_name}</b>?",
                f"mod_topic_moderators_{extra_id}"
            )

        return ("Вы уверены?", "admin_main")

    @staticmethod
    def sterile_command(redirect: bool = False, error_prefix: str = "меню"):
        """
        Декоратор для командных хендлеров.
        Автоматизирует редирект в ЛС, удаление триггеров и трекинг меню.
        Хендлер должен возвращать: (text, reply_markup) или просто text.
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
                # Вызываем хендлер для получения данных
                result = await func(message, state, *args, **kwargs)

                if result is None:
                    return

                # Распаковываем (текст, клавиатура)
                if isinstance(result, tuple):
                    text, reply_markup = result
                else:
                    text, reply_markup = result, None

                # Делегируем отправку стандартному методу
                return await UIService.send_redirected_menu(
                    message=message,
                    state=state,
                    text=text,
                    reply_markup=reply_markup,
                    error_prefix=error_prefix if redirect else None
                )
            return wrapper
        return decorator

    @staticmethod
    def format_user_card(user_id: int, user_name: str, groups_str: str, roles: list, available_topics: list) -> str:
        """
        Красивое оформление карточки пользователя с ролями и топиками.
        roles: список кортежей (role_name, topic_id) — topic_id может быть None.
        available_topics: список кортежей (topic_id, topic_name).
        Имя топика для модератора берётся из available_topics — без обращения к БД.
        UI-сервис не должен знать о слое БД.
        """
        # Индекс имён топиков — строим из переданных данных
        topic_name_map = {t_id: t_name for t_id, t_name in available_topics}

        # Сортируем роли
        role_priority = {"superadmin": 0, "admin": 1, "moderator": 2}
        sorted_roles = sorted(roles, key=lambda x: role_priority.get(x[0], 99))

        role_blocks = []
        is_global_admin = False
        for r_name, t_id in sorted_roles:
            if r_name in ["superadmin", "admin"]:
                is_global_admin = True
                role_blocks.append(
                    "┌── 👑 <b>АДМИНИСТРАТОР</b> ──┐\n"
                    "│  <i>Глобальный доступ</i>\n"
                    "└───────────────────┘"
                )
            elif r_name == "moderator":
                # Имя берётся из переданного индекса, без обращения к БД из UI-слоя
                t_name = topic_name_map.get(t_id, f"ID:{t_id}" if t_id else "???")
                role_blocks.append(
                    f"┌── 🛡 <b>МОДЕРАТОР</b> ──┐\n"
                    f"│  <b>Топик:</b> {t_name}\n"
                    f"└──────────────────┘"
                )

        roles_display = "\n".join(role_blocks) if role_blocks else "👤 <b>Участник</b>"

        # Топики
        if is_global_admin:
            topics_display = "  • <b>Все топики (Глобальный доступ)</b>"
        else:
            topics_display = (
                "\n".join([f"  • {t_name} (ID: {t_id})" for t_id, t_name in available_topics])
                if available_topics else "  <i>нет доступных топиков</i>"
            )

        text = (
            f"{roles_display}\n\n"
            f"👤 <b>Профиль:</b> {user_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📂 <b>Шаблоны:</b> {groups_str}\n\n"
            f"📍 <b>Доступные топики:</b>\n{topics_display}"
        )
        return text