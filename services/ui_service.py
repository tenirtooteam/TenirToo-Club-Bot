# Файл: services/ui_service.py
import logging
from functools import wraps
from aiogram import Bot, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import callbacks as cb

logger = logging.getLogger(__name__)


class _RouteNotResolved:
    """Часовой: типизированный путь не признал маршрут своим.

    Отдельный объект, а не None: None — легальный результат экрана.
    """

    __slots__ = ()


_ROUTE_NOT_RESOLVED = _RouteNotResolved()


class UIService:
    # [feature 011 / FR-005] PAGINATED_CMDS удалён. Это был второй, дублирующий
    # реестр — список имён команд, «умеющих» страницу. Страничность теперь следует
    # из наличия поля `page` у объявления маршрута; расходиться двум источникам
    # правды больше негде.

    @staticmethod
    async def delete_tracked_ui(state: FSMContext, bot: Bot, chat_id: int):
        """Удаляет все запомненные системные сообщения (стек last_menu_ids)."""
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
    async def terminate_input(state: FSMContext, message: types.Message, reset_state: bool = True):
        """
        Единый метод завершения FSM-ввода:
        удаляет tracked_ui и сообщение пользователя, сбрасывает состояние.
        """
        await UIService.delete_tracked_ui(state, message.bot, message.chat.id)
        await UIService.delete_msg(message)
        if reset_state:
            await state.set_state(None)

    @staticmethod
    async def clear_fsm_data_safely(state: FSMContext):
        """
        Очищает все FSM данные, кроме служебных ключей Стерильного интерфейса
        (last_menu_ids, last_menu_id и admin_onboarded).
        """
        data = await state.get_data()
        clean_data = {}
        for key in ["last_menu_ids", "last_menu_id", "admin_onboarded"]:
            if key in data:
                clean_data[key] = data[key]
        await state.set_data(clean_data)


    @staticmethod
    async def sterile_redirect(
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
            await UIService.terminate_input(state, message, reset_state=False)
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
    async def sterile_show(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        text: str,
        reply_markup: types.InlineKeyboardMarkup = None,
        parse_mode: str = "HTML"
    ):
        """
        Отображение/обновление меню по стерильному протоколу:
        - Если CallbackQuery — редактирует (swap) текущее сообщение.
        - Если Message — вызывает terminate_input и шлет новое.
        """
        is_cb = isinstance(event, types.CallbackQuery)

        if is_cb:
            try:
                await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except TelegramBadRequest as e:
                err_str = str(e).lower()
                if "message is not modified" in err_str:
                    pass  # Контент идентичен — это нормально
                elif "button_type_invalid" in err_str:
                    logger.error("❌ [UI] CRITICAL: Invalid button configuration detected!")
                    logger.error(f"Markup: {reply_markup}")
                    # Шлем новое сообщение без битой клавы (или пробуем принудительно)
                    new_msg = await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                    await UIService.delete_msg(event.message)
                    await state.update_data(last_menu_ids=[new_msg.message_id])
                else:
                    # Реальная ошибка: сообщение старое или удалено — отправляем новое
                    logger.warning(f"⚠️ [UI] edit_text failed ({e}), sending new message.")
                    new_msg = await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                    await UIService.delete_msg(event.message)
                    await state.update_data(last_menu_ids=[new_msg.message_id])
            except Exception as e:
                logger.error(f"❌ [UI] Unexpected error in show_menu: {e}", exc_info=True)
                # Fallback: пробуем отправить новое сообщение
                try:
                    new_msg = await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                    await state.update_data(last_menu_ids=[new_msg.message_id])
                except Exception:
                    pass

            try:
                await event.answer()
            except Exception:
                pass  # Callback уже был закрыт — это нормально
        else:
            # Если это сообщение (текстовый ввод), чистим чат (стерильная терминация)
            await UIService.terminate_input(state, event, reset_state=False)
            new_msg = await event.bot.send_message(
                event.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            await state.update_data(last_menu_ids=[new_msg.message_id])


    @staticmethod
    async def sterile_ask(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        text: str,
        state_to_set=None,
        reply_markup=None
    ):
        """
        Убивает предыдущий UI (delete_tracked_ui), шлет промпт и ставит на слежение.
        """
        bot = event.bot if isinstance(event, types.Message) else event.message.bot
        chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id

        await UIService.delete_tracked_ui(state, bot, chat_id)

        if isinstance(event, types.Message):
            await UIService.delete_msg(event)

        msg_source = event if isinstance(event, types.Message) else event.message
        sent = await msg_source.answer(text, reply_markup=reply_markup, parse_mode="HTML")

        await state.update_data(last_menu_ids=[sent.message_id])
        if state_to_set:
            await state.set_state(state_to_set)
        return sent
    @staticmethod
    async def get_landing_data(user_id: int, role_override: str = None) -> tuple[str, any]:
        """
        Определяет стартовый экран для пользователя в зависимости от прав [CP-3.13].
        Параметр role_override позволяет принудительно показать конкретную панель (для алиасов /admin, /mod).
        Возвращает (text, keyboard_func).
        """
        from services.permission_service import PermissionService
        import keyboards as kb

        # 1. Принудительный выбор роли (debug aliases)
        if role_override == "admin":
            return "🛠 <b>Панель управления</b>", kb.main_admin_kb
        elif role_override == "moderator":
            manageable = PermissionService.get_manageable_topics(user_id)
            if not manageable:
                return "❌ У вас нет прав модератора.", None
            return "🛠 <b>Панель модератора</b>\nВыберите топик:", lambda: kb.moderator_topics_list_kb(manageable)

        # 2. Обычный Traffic Controller (автоматический выбор)
        # 2.1 Глобальный админ
        if PermissionService.is_global_admin(user_id):
            return "🛠 <b>Панель управления</b>", kb.main_admin_kb

        # 2.2 Модератор (есть хотя бы один управляемый топик)
        manageable = PermissionService.get_manageable_topics(user_id)
        if manageable:
            return "🛠 <b>Панель модератора</b>\nВыберите топик:", lambda: kb.moderator_topics_list_kb(manageable)

        # 2.3 Обычный участник
        return (
            "Привет! 👋\n\n"
            "Добро пожаловать в круг друзей клуба <b>«Теңир-Too»</b>.\n\n"
            "Я твой походный гид. Помогу записаться в горы, найти нужные обсуждения или проверить свой профиль.\n\n"
            "Выбирай, с чего начнем:",
            kb.user_main_kb
        )

    @staticmethod
    async def _resolve_typed_route(state, event, callback_data):
        """Разрешает маршрут через реестр объявлений. Иначе — часовой.

        Возвращает `_ROUTE_NOT_RESOLVED`, если маршрут не относится к
        мигрированному семейству: тогда навигатор уходит на старый путь.

        Битые данные УЖЕ мигрированного маршрута — не «чужой маршрут», а отказ:
        уводим в защитный возврат, не давая старой цепочке подобрать их
        подстрокой и увести на случайный экран.
        """
        if isinstance(callback_data, CallbackData):
            entry = _ROUTE_REGISTRY.get(type(callback_data).__prefix__)
            if entry is None:
                return _ROUTE_NOT_RESOLVED
            return await entry[1](state, event, callback_data)

        prefix = cb.route_prefix(str(callback_data))
        entry = _ROUTE_REGISTRY.get(prefix)
        if entry is None:
            return _ROUTE_NOT_RESOLVED

        factory, render = entry
        try:
            data = factory.unpack(str(callback_data))
        except (TypeError, ValueError) as e:
            # Тот же кортеж, что ловит CallbackQueryFilter в aiogram (D-1):
            # расхождение «фильтр пропустил / навигатор упал» невозможно.
            logger.warning(
                f"⚠️ [NAVIGATOR] Битые данные маршрута {prefix!r}: {callback_data!r} ({type(e).__name__}: {e})"
            )
            return await UIService.show_admin_dashboard(
                state, event, text="⚠️ Ошибка навигации. Возврат в главное меню:"
            )

        return await render(state, event, data)

    @staticmethod
    async def generic_navigator(
        state: FSMContext,
        event: types.Message | types.CallbackQuery,
        callback_data: "str | CallbackData",
    ):
        """Ультимативный роутер: маршрут -> UI экран.

        [feature 011] Принимает либо объявление маршрута (`CallbackData`), либо
        строку. Имя параметра сохранено — `R-UI-3` фиксирует имя и обязанность
        Defensive Routing, а не тип (research.md D-6).

        Порядок разрешения (contracts/callback-routes.md §C-4):
          1. объект `CallbackData` -> реестр по префиксу, уже разобран;
          2. строка, чей префикс есть в реестре -> `unpack()` -> экран;
          3. иначе -> старый путь (словарь простых маршрутов + цепочка ветвлений);
          4. промах или `(TypeError, ValueError)` -> защитный возврат.

        Шаг 3 — переходный: пока мигрированы не все семейства, строки старого
        формата (`user_info_5`) обязаны продолжать работать. Он удаляется в
        фазе 5, когда станет доказуемо мёртвым.
        """
        from database import db
        import keyboards as kb
        from services.permission_service import PermissionService

        user_id = event.from_user.id

        # 0. Типизированный путь: точное сопоставление с объявленным контрактом.
        resolved = await UIService._resolve_typed_route(state, event, callback_data)
        if resolved is not _ROUTE_NOT_RESOLVED:
            return resolved

        # Дальше — только строки: объект сюда дойти не может (см. _resolve_typed_route).
        callback_data = str(callback_data)

        # 1. Глобальная навигация (Simple)
        simple = {
            "admin_main": ("🛠 <b>Штаб управления</b>\nЗдесь настраивается жизнь всего клуба.", kb.main_admin_kb),
            "user_main": ("🏠 <b>Главное меню</b>\nТвой личный пульт управления приключениями:", kb.user_main_kb),
            "user_profile_view": (None, None), # Специальная обработка ниже
            "roles_dashboard": ("🛡 <b>Центр ответственности</b>\nКто за что отвечает в клубе:", lambda: kb.roles_dashboard_kb(PermissionService.is_global_admin(user_id))),
            "roles_faq": ("🛡 <b>Описание ролей</b>\n\n👑 <b>Админ</b>: Видит всё, управляет всеми процессами.\n🛡 <b>Модератор</b>: Хранитель порядка в конкретном топике.\n👤 <b>Участник</b>: Тот, ради кого мы всё это затеяли.", kb.back_to_roles_dashboard_kb),
            "templates_faq": (None, None), # Redirects to help_service logic
            "event_list": ("📅 <b>Наши приключения</b>\nАктуальные выезды и походы:", lambda: kb.get_events_list_kb(db.get_active_events())),
            "event_pending_list": ("⏳ <b>Новые заявки</b>\nПоходы, ожидающие одобрения:", lambda: kb.get_events_list_kb(db.get_pending_events(), is_admin=True)),
            "landing": (None, None), # Специальный вызов через get_landing_data
        }

        # [feature 011 / FR-005] Прежде номер страницы отрезался отсюда как
        # `split("_pg_")[1]` — это и был источник DEF-1/DEF-2. Теперь страница —
        # объявленное поле фабрики, а сюда доходят только беспараметрические
        # маршруты, у которых её нет.
        cmd = callback_data
        if cmd in simple:
            await state.set_state(None)
            await UIService.clear_fsm_data_safely(state)
            text, kb_func = simple[cmd]

            # 1.1 Специальные редиректы
            if cmd == "templates_faq":
                return await UIService.generic_navigator(state, event, cb.HelpCB(key="templates", back_data="manage_groups"))

            if cmd == "user_profile_view":
                # Переходим к блоку "Инфо-карточки" ниже
                pass
            elif cmd == "landing":
                text, kb_func = await UIService.get_landing_data(user_id)
                return await UIService.sterile_show(state, event, text, reply_markup=kb_func())
            elif kb_func is not None:
                return await UIService.sterile_show(state, event, text, reply_markup=kb_func())

        # [feature 011] Здесь разбирался старый формат справки `help:{key}:{back}`
        # ручным `split(":")` с позиционным `parts[1]`/`parts[2]`. Удалён: справку
        # разрешает реестр через HelpCB, а строка старого формата до сюда не
        # доходит — её отбраковывает unpack() в защитный возврат (C-7).

        # 2. Специальные экраны, которым не нужен параметр.
        if cmd == "user_profile_view":
            user_name = db.get_user_name(user_id)
            user_templates = db.get_user_group_templates(user_id)
            groups_str = ", ".join(g[1] for g in user_templates) if user_templates else "нет назначенных шаблонов"
            roles = list(db.get_user_roles(user_id))
            available_topics = db.get_user_available_topics(user_id)
            text = UIService.format_user_card(user_id, user_name, groups_str, roles, available_topics)
            return await UIService.sterile_show(state, event, text, reply_markup=kb.user_profile_kb())

        # [feature 011] Здесь жила цепочка подстрочных ветвлений на ~80 строк:
        # `if "user_info" in cmd`, `if "topic_" in cmd and ("global" in cmd or
        # "in_group" in cmd)` и позиционный разбор `int(p[-1])` / `int(p[3])`.
        # Удалена: маршруты семейства разрешает реестр (_ROUTE_REGISTRY) по точному
        # ключу, параметры приезжают по имени поля. Именно в этой цепочке жили все
        # три дефекта — DEF-1, DEF-2, DEF-3 (research.md §2).
        #
        # Мёртвой доказана зондом: за полный прогон сюда доходят только постоянные
        # маршруты и неизвестные строки, ни одной параметризованной.

        # Резервный лог и сброс на главное меню (если что-то пошло не так)
        logger.warning(f"⚠️ [NAVIGATOR] Неизвестная команда или некорректные данные: {cmd} (data: {callback_data})")
        await UIService.show_admin_dashboard(state, event, text="⚠️ Ошибка навигации. Возврат в главное меню:")

    @staticmethod
    async def show_admin_dashboard(state: FSMContext, event: types.Message | types.CallbackQuery, text: str = "🛠 <b>Панель управления</b>"):
        """Отображает главную панель администратора с сессионным онбордингом."""
        import keyboards as kb

        state_data = await state.get_data()
        if not state_data.get("admin_onboarded"):
            text_onboarding = (
                "🏔 <b>Добро пожаловать в Панель управления!</b>\n\n"
                "Перед началом работы ознакомьтесь с ключевыми принципами взаимодействия с ботом:\n\n"
                "1. 🧹 <b>Стерильный интерфейс (Sterile UI)</b>: Бот автоматически удаляет старые сообщения меню "
                "при переходах, чтобы чат оставался чистым. Не пытайтесь кликать по старым кнопкам в истории "
                "чата — они блокируются и стираются.\n"
                "2. 🛡️ <b>Закрыто по умолчанию (Default Deny)</b>: Любые новые топики группы закрыты для участников. "
                "Вы должны явно настроить и применить права доступа для каждого топика в панели управления.\n\n"
                "Нажмите кнопку ниже, чтобы подтвердить ознакомление и войти."
            )
            markup = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🏔 Начать работу", callback_data="admin_confirm_onboarding")],
                [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")]
            ])
            return await UIService.sterile_show(state, event, text_onboarding, reply_markup=markup)

        await UIService.sterile_show(state, event, text, reply_markup=kb.main_admin_kb())

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

        await UIService.sterile_show(state, event, text, reply_markup=kb.user_edit_kb(user_id, is_superadmin=is_sa))

    @staticmethod
    async def show_group_detail(state: FSMContext, event: types.Message | types.CallbackQuery, group_id: int):
        """Отображает информацию о группе."""
        from database import db
        import keyboards as kb

        g_name = db.get_group_name(group_id)
        topics_count = len(db.get_topics_of_group(group_id))
        text = f"📂 <b>Группа:</b> {g_name}\n📍 <b>Топиков:</b> {topics_count}"
        await UIService.sterile_show(state, event, text, reply_markup=kb.group_edit_kb(group_id))

    @staticmethod
    async def show_topic_detail(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int, group_id: int = 0):
        """Отображает информацию о топике."""
        from database import db
        import keyboards as kb

        t_name = db.get_topic_name(topic_id)
        access_groups = db.get_groups_by_topic(topic_id)
        if not db.is_topic_restricted(topic_id):
            status_str = "🔐 <b>Только администрация</b> (Default Deny)"
        else:
            status_str = ", ".join(access_groups) if access_groups else "НЕТ АКТИВНЫХ ГРУПП"

        text = (
            f"📍 <b>Информация о топике</b>\n\n"
            f"<b>Наименование:</b> {t_name}\n"
            f"<b>ID:</b> <code>{topic_id}</code>\n"
            f"<b>Доступ имеют:</b> {status_str}"
        )
        await UIService.sterile_show(state, event, text, reply_markup=kb.topic_edit_kb(topic_id, group_id=group_id))

    @staticmethod
    async def show_moderator_groups(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int, page: int = 1):
        """Отображает список групп для модератора топика."""
        from database import db
        import keyboards as kb
        t_name = db.get_topic_name(topic_id)
        text = f"📂 <b>Группы доступа для топика {t_name}</b>"
        await UIService.sterile_show(state, event, text, reply_markup=kb.moderator_group_list_kb(topic_id, page=page))

    @staticmethod
    async def show_moderator_moderators(state: FSMContext, event: types.Message | types.CallbackQuery, topic_id: int):
        """Отображает список модераторов топика."""
        from database import db
        import keyboards as kb
        t_name = db.get_topic_name(topic_id)
        text = f"👑 <b>Модераторы топика {t_name}</b>"
        await UIService.sterile_show(state, event, text, reply_markup=kb.moderator_topic_moderators_kb(topic_id))

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
                cb.GroupInfoCB(group_id=target_id).pack()
            )
        elif action == "topic_del" or action == "mod_topic_del":
            name = ManagementService.get_entity_name("topic", target_id)
            g_name = ManagementService.get_entity_name("group", extra_id)
            back = cb.TopicInGroupCB(topic_id=target_id, group_id=extra_id).pack() if action == "topic_del" else cb.ModTopicGroupsCB(topic_id=target_id).pack()
            return (f"❓ Убрать топик <b>{name}</b> из группы <b>{g_name}</b>?", back)

        elif action == "global_topic_del":
            name = ManagementService.get_entity_name("topic", target_id)
            return (
                f"⚠️ <b>КРИТИЧЕСКОЕ ДЕЙСТВИЕ!</b>\n\nУдалить топик <b>{name}</b> из БД?\n<i>Это очистит все привязки и роли!</i>",
                cb.TopicGlobalViewCB(topic_id=target_id).pack()
            )
        elif action == "user_del":
            name = ManagementService.get_entity_name("user", target_id)
            return (
                f"⚠️ <b>ВНИМАНИЕ!</b>\n\nУдалить пользователя <b>{name}</b> (ID: {target_id})?\n<i>Это аннулирует все его доступы!</i>",
                cb.UserInfoCB(user_id=target_id).pack()
            )
        elif action.startswith("role_rev"):
            name = ManagementService.get_entity_name("user", target_id)
            role_id = int(action.split("_")[-1]) if action != "role_rev" else 0
            role_name = db.get_role_name_by_id(role_id) if role_id else "роль"
            context = f"топика {db.get_topic_name(extra_id)}" if extra_id else "глобально"
            return (
                f"❓ Отозвать роль <b>{role_name}</b> у пользователя <b>{name}</b> ({context})?",
                cb.UserRolesManageCB(user_id=target_id).pack()
            )
        elif action == "event_del":
            name = ManagementService.get_entity_name("event", target_id)
            return (
                f"⚠️ <b>ВНИМАНИЕ!</b>\n\nВы действительно хотите удалить поход <b>{name}</b>?\n<i>Это действие нельзя отменить!</i>",
                f"event_view:{target_id}"
            )
        elif action == "mod_rem":
            name = ManagementService.get_entity_name("user", target_id)
            t_name = ManagementService.get_entity_name("topic", extra_id)
            return (
                f"❓ Снять права модератора с <b>{name}</b> в топике <b>{t_name}</b>?",
                cb.ModTopicModeratorsCB(topic_id=extra_id).pack()
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
                return await UIService.sterile_redirect(
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


# =============================================================================
# [feature 011] Реестр маршрутов: объявление -> экран.
#
# Заменяет цепочку подстрочных ветвлений внутри generic_navigator. Ключ —
# префикс объявления, поиск ТОЧНЫЙ (dict), а не по вхождению: коллизия имён,
# которую допускал `"user_info" in cmd`, здесь невозможна by construction.
#
# Параметры экранов приезжают по ИМЕНИ поля. Позиционного разбора (p[-1], p[3])
# в этом пути нет — в нём и жили DEF-1/DEF-2/DEF-3.
#
# Заполняется по семьям маршрутов: пока здесь только непаджинируемые (фаза 3),
# паджинируемые придут в фазе 4. Остальные обслуживает старый путь.
# =============================================================================


async def _render_user_info(state, event, data: cb.UserInfoCB):
    return await UIService.show_user_detail(state, event, data.user_id)


async def _render_group_info(state, event, data: cb.GroupInfoCB):
    return await UIService.show_group_detail(state, event, data.group_id)


async def _render_topic_global_view(state, event, data: cb.TopicGlobalViewCB):
    return await UIService.show_topic_detail(state, event, data.topic_id, 0)


async def _render_topic_in_group(state, event, data: cb.TopicInGroupCB):
    """[FR-017 / фикс DEF-3] Топик и группа уходят по назначению.

    Старый путь звал show_topic_detail(int(p[-1]), int(p[-2])) — то есть
    group_id уезжал в параметр topic_id, и открывалась карточка чужого топика.
    Здесь перепутать нечего: поля адресуются по имени.
    """
    return await UIService.show_topic_detail(state, event, data.topic_id, data.group_id)


async def _render_u_topic_info(state, event, data: cb.UserTopicInfoCB):
    from database import db
    import keyboards as kb

    t_id = data.topic_id
    t_name = db.get_topic_name(t_id)
    access_groups = db.get_groups_by_topic(t_id)
    groups_str = "\n".join(f"— {g}" for g in access_groups) if access_groups else "Доступ не настроен"
    has_access = db.can_write(event.from_user.id, t_id)
    access_status = "✅ У тебя есть доступ." if has_access else "❌ У тебя нет доступа."
    text = (
        f"📍 <b>Информация о топике</b>\n\n"
        f"<b>Название:</b> {t_name}\n"
        f"<b>ID:</b> <code>{t_id}</code>\n\n"
        f"👥 <b>Связанные шаблоны:</b>\n{groups_str}\n\n"
        f"🔐 <b>Твой статус:</b> {access_status}\n\n"
        f"<i>Если доступа нет, твои сообщения в этом топике будут удаляться автоматически.</i>"
    )
    return await UIService.sterile_show(state, event, text, reply_markup=kb.user_topic_detail_kb(t_id))


async def _render_mod_topic_select(state, event, data: cb.ModTopicSelectCB):
    from database import db
    import keyboards as kb

    t_id = data.topic_id
    return await UIService.sterile_show(
        state, event, f"📍 <b>Управление: {db.get_topic_name(t_id)}</b>",
        kb.moderator_topic_menu_kb(t_id),
    )


async def _render_user_roles_manage(state, event, data: cb.UserRolesManageCB):
    from database import db
    import keyboards as kb

    u_id = data.user_id
    return await UIService.sterile_show(
        state, event, f"🛡 <b>Роли пользователя: {db.get_user_name(u_id)}</b>",
        kb.user_roles_manage_kb(u_id),
    )


async def _render_help(state, event, data: cb.HelpCB):
    from handlers.common import show_help_view

    return await show_help_view(state, event, key=data.key, back_data=data.back_data)


_ROUTE_REGISTRY: "dict[str, tuple[type[CallbackData], object]]" = {
    cb.UserInfoCB.__prefix__: (cb.UserInfoCB, _render_user_info),
    cb.GroupInfoCB.__prefix__: (cb.GroupInfoCB, _render_group_info),
    cb.TopicGlobalViewCB.__prefix__: (cb.TopicGlobalViewCB, _render_topic_global_view),
    cb.TopicInGroupCB.__prefix__: (cb.TopicInGroupCB, _render_topic_in_group),
    cb.UserTopicInfoCB.__prefix__: (cb.UserTopicInfoCB, _render_u_topic_info),
    cb.ModTopicSelectCB.__prefix__: (cb.ModTopicSelectCB, _render_mod_topic_select),
    cb.UserRolesManageCB.__prefix__: (cb.UserRolesManageCB, _render_user_roles_manage),
    cb.HelpCB.__prefix__: (cb.HelpCB, _render_help),
}


# --- Паджинируемые маршруты (фаза 4) --------------------------------------
# Номер страницы приезжает объявленным полем, а не отрезается от строки.
# Экраны и тексты — дословно из старого пути: фича меняет механизм, не
# содержание (FR-014).


async def _reset_fsm(state: FSMContext):
    """Сбрасывает состояние ввода перед показом экрана верхнего уровня.

    [FR-007] Точная копия того, что делал старый путь внутри `if cmd in simple`.
    Асимметрия не случайна и не подлежит «выравниванию»: экраны верхнего уровня
    (списки, панели) сбрасывают незавершённый ввод, экраны-карточки — нет.
    Зовут её только те маршруты, что жили в словаре `simple`; переезд в реестр
    обязан сохранить это ровно как было (`R-FSM-1`).
    """
    await state.set_state(None)
    await UIService.clear_fsm_data_safely(state)


async def _render_manage_groups(state, event, data: cb.ManageGroupsCB):
    import keyboards as kb

    await _reset_fsm(state)
    return await UIService.sterile_show(
        state, event,
        "📂 <b>Шаблоны доступа</b>\nГрупповые правила для выдачи прав:",
        reply_markup=kb.groups_list_kb(page=data.page),
    )


async def _render_manage_users(state, event, data: cb.ManageUsersCB):
    import keyboards as kb

    await _reset_fsm(state)
    return await UIService.sterile_show(
        state, event,
        "👥 <b>Клубный реестр</b>\nСписок всех участников:",
        reply_markup=kb.users_list_kb(page=data.page),
    )


async def _render_all_topics_list(state, event, data: cb.AllTopicsListCB):
    import keyboards as kb

    await _reset_fsm(state)
    return await UIService.sterile_show(
        state, event,
        "📍 <b>Все локации</b>\nПолный список топиков форума:",
        reply_markup=kb.all_topics_kb(page=data.page),
    )


async def _render_list_users_roles(state, event, data: cb.ListUsersRolesCB):
    """Список ответственных лиц.

    Переиспользует users_list_kb, чьи стрелки помечены маршрутом `manage_users`.
    Поэтому переход на стр. 2 уводит на «Клубный реестр» — другой заголовок, тот
    же список. Поведение существует сегодня; фича его сохраняет, а не чинит:
    в санкционированный список FR-015…FR-017 оно не входит. Зафиксировано
    характеризацией, заведено в роадмап.
    """
    import keyboards as kb

    await _reset_fsm(state)
    return await UIService.sterile_show(
        state, event,
        "📋 <b>Ответственные лица</b>\nСписок всех пользователей с особыми правами:",
        reply_markup=kb.users_list_kb(page=data.page),
    )


async def _render_user_topics(state, event, data: cb.UserTopicsCB):
    import keyboards as kb

    await _reset_fsm(state)
    return await UIService.sterile_show(
        state, event,
        "📍 <b>Твои маршруты</b>\nСписок топиков, где ты можешь общаться:",
        reply_markup=kb.user_topics_list_kb(event.from_user.id, page=data.page),
    )


async def _render_moderator(state, event, data: cb.ModeratorCB):
    import keyboards as kb
    from services.permission_service import PermissionService

    await _reset_fsm(state)
    manageable = PermissionService.get_manageable_topics(event.from_user.id)
    return await UIService.sterile_show(
        state, event,
        "🛠 <b>Инструменты хранителя</b>\nВыбери топик для управления:",
        reply_markup=kb.moderator_topics_list_kb(manageable, page=data.page),
    )


async def _render_group_topics_list(state, event, data: cb.GroupTopicsListCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"📍 <b>Топики группы: {db.get_group_name(data.group_id)}</b>",
        kb.group_topics_list_kb(data.group_id, page=data.page),
    )


async def _render_mod_topic_groups(state, event, data: cb.ModTopicGroupsCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"📂 <b>Группы топика: {db.get_topic_name(data.topic_id)}</b>",
        kb.moderator_group_list_kb(data.topic_id, page=data.page),
    )


async def _render_mod_topic_moderators(state, event, data: cb.ModTopicModeratorsCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"👑 <b>Модераторы: {db.get_topic_name(data.topic_id)}</b>",
        kb.moderator_topic_moderators_kb(data.topic_id, page=data.page),
    )


async def _render_mod_gr_addlist(state, event, data: cb.ModGroupAddListCB):
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        "🔗 <b>Привязка группы:</b>",
        kb.moderator_available_groups_kb(data.topic_id, page=data.page),
    )


async def _render_mod_users_manage(state, event, data: cb.ModUsersManageCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"👥 <b>Юзеры топика: {db.get_topic_name(data.topic_id)}</b>",
        kb.moderator_users_list_kb(data.topic_id, page=data.page),
    )


async def _render_user_templates_manage(state, event, data: cb.UserTemplatesManageCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"🔐 <b>Шаблоны пользователя: {db.get_user_name(data.user_id)}</b>",
        kb.user_groups_edit_kb(data.user_id, page=data.page),
    )


async def _render_tmpl_act_start(state, event, data: cb.TmplActStartCB):
    import keyboards as kb

    title = (
        "⚡ Выберите топик для ПРИМЕНЕНИЯ шаблона:"
        if data.action == cb.TemplateAction.APPLY
        else "🔄 Выберите топик для СИНХРОНИЗАЦИИ с шаблоном:"
    )
    return await UIService.sterile_show(
        state, event, title,
        reply_markup=kb.template_action_topic_select_kb(
            data.group_id, data.action.value, page=data.page
        ),
    )


async def _render_topic_assign(state, event, data: cb.TopicAssignCB):
    from database import db
    import keyboards as kb

    return await UIService.sterile_show(
        state, event,
        f"📍 <b>Выбор топика для: {db.get_user_name(data.user_id)}</b>",
        kb.topic_selection_for_role_kb(data.user_id, page=data.page),
    )


_ROUTE_REGISTRY.update({
    cb.ManageGroupsCB.__prefix__: (cb.ManageGroupsCB, _render_manage_groups),
    cb.ManageUsersCB.__prefix__: (cb.ManageUsersCB, _render_manage_users),
    cb.AllTopicsListCB.__prefix__: (cb.AllTopicsListCB, _render_all_topics_list),
    cb.ListUsersRolesCB.__prefix__: (cb.ListUsersRolesCB, _render_list_users_roles),
    cb.UserTopicsCB.__prefix__: (cb.UserTopicsCB, _render_user_topics),
    cb.ModeratorCB.__prefix__: (cb.ModeratorCB, _render_moderator),
    cb.GroupTopicsListCB.__prefix__: (cb.GroupTopicsListCB, _render_group_topics_list),
    cb.ModTopicGroupsCB.__prefix__: (cb.ModTopicGroupsCB, _render_mod_topic_groups),
    cb.ModTopicModeratorsCB.__prefix__: (cb.ModTopicModeratorsCB, _render_mod_topic_moderators),
    cb.ModGroupAddListCB.__prefix__: (cb.ModGroupAddListCB, _render_mod_gr_addlist),
    cb.ModUsersManageCB.__prefix__: (cb.ModUsersManageCB, _render_mod_users_manage),
    cb.UserTemplatesManageCB.__prefix__: (cb.UserTemplatesManageCB, _render_user_templates_manage),
    cb.TmplActStartCB.__prefix__: (cb.TmplActStartCB, _render_tmpl_act_start),
    cb.TopicAssignCB.__prefix__: (cb.TopicAssignCB, _render_topic_assign),
})
