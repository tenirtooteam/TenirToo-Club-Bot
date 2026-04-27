# Файл: services/management_service.py
import logging
import html
from typing import Optional, List
from aiogram.types import User
from aiogram import Bot
from database import db
from services.permission_service import PermissionService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ManagementService:
    """
    Единый сервис управления сущностями проекта (Пользователи, Группы, Роли).
    Обслуживает как хендлеры администратора, так и модератора.
    """

    # Лимиты для строк (защита UI)
    MAX_NAME_LENGTH = 64

    # Лимиты SQLite INTEGER (64-бит со знаком)
    SQLITE_MIN_INT = -9223372036854775808
    SQLITE_MAX_INT = 9223372036854775807

    @staticmethod
    def create_quick_event(user_id: int, title: str) -> int:
        """
        Создает 'быстрое' мероприятие (без даты, авто-одобрение).
        Централизует создание для анонсов. [PL-2.2.18]
        """
        import datetime
        now_iso = datetime.datetime.now().strftime("%Y-%m-%d")
        event_id = db.create_event(
            title=title,
            start_date="Оперативно",
            end_date=None,
            creator_id=user_id,
            is_approved=1,
            start_iso=now_iso,
            end_iso=now_iso
        )
        if event_id > 0:
            db.add_event_participant(event_id, user_id)
            db.add_event_lead(event_id, user_id)
            logger.info(f"⚡ Квик-ивент создан: {title} (ID: {event_id})")
        return event_id

    @staticmethod
    async def ensure_user_registered(user: User):
        """Проверяет наличие пользователя и регистрирует при необходимости."""
        user_id = user.id
        if not db.user_exists(user_id):
            f_name = user.first_name
            l_name = user.last_name or ""

            # Логика именования по умолчанию
            if not f_name and not l_name:
                f_name = f"Пользователь_{user_id}"
            elif not f_name:
                f_name = l_name
                l_name = ""

            db.add_user(user_id, f_name, l_name)
            logger.info(f"🆕 Авто-регистрация: {f_name} {l_name} (ID: {user_id})")
            ManagementService._trigger_sheets_sync("users")

    @staticmethod
    def _parse_and_validate_id(user_input: str) -> tuple[int, str]:
        """
        Внутренний помощник для безопасного парсинга ID.
        Возвращает (ID, error_signal).
        Если ID валиден, error_signal = "".
        Если не число, error_signal = "SEARCH_REQUIRED".
        Если число вне диапазона, error_signal = "❌ Ошибка: ID вне диапазона БД."
        """
        if not user_input.isdigit():
            return 0, "SEARCH_REQUIRED"

        val = int(user_input)
        if not (ManagementService.SQLITE_MIN_INT <= val <= ManagementService.SQLITE_MAX_INT):
            return 0, "❌ Ошибка: ID слишком длинный для базы данных."

        return val, ""

    @staticmethod
    def add_user(user_data_text: str) -> tuple[bool, str]:
        """Логика создания нового пользователя с поддержкой пробелов в именах."""
        parts = user_data_text.strip().split()
        if len(parts) < 2:
            return False, "❌ Формат: ID Имя [Фамилия]"

        user_id, err = ManagementService._parse_and_validate_id(parts[0])
        if err:
            msg = err if err != "SEARCH_REQUIRED" else "❌ ID должен быть числом."
            return False, msg

        # Все, что после ID, считаем именем и фамилией
        name_parts = parts[1:]
        if len(name_parts) == 1:
            f_name, l_name = name_parts[0], ""
        else:
            # Если частей больше двух, склеиваем в Имя и Фамилию (последнее слово — фамилия)
            f_name = " ".join(name_parts[:-1])
            l_name = name_parts[-1]

        f_name, l_name = html.escape(f_name), html.escape(l_name)
        
        if len(f_name) > ManagementService.MAX_NAME_LENGTH or len(l_name) > ManagementService.MAX_NAME_LENGTH:
            return False, f"❌ Ошибка: Имя/Фамилия не должны превышать {ManagementService.MAX_NAME_LENGTH} симв."

        if db.add_user(user_id, f_name, l_name):
            ManagementService._trigger_sheets_sync("users")
            return True, f"✅ Пользователь {f_name} добавлен!"

        return False, f"❌ Ошибка: ID {user_id} уже занят или сбой БД."

    @staticmethod
    def create_group(name: str) -> tuple[bool, str]:
        """Логика создания новой группы доступа."""
        name = html.escape(name.strip())
        if not name:
            return False, "❌ Название группы не может быть пустым."
        
        if len(name) > ManagementService.MAX_NAME_LENGTH:
            return False, f"❌ Ошибка: Название не должно превышать {ManagementService.MAX_NAME_LENGTH} симв."

        group_id = db.create_group(name)
        if group_id > 0:
            ManagementService._trigger_sheets_sync("groups")
            return True, f"✅ Группа <b>{name}</b> создана!"

        return False, "❌ Не удалось создать группу в базе данных."

    @staticmethod
    def assign_moderator_role_by_id(target_user_id: int, topic_id: int) -> tuple[bool, str]:
        """Прямое назначение модератора по ID."""
        if PermissionService.is_moderator_of_topic(target_user_id, topic_id):
            return False, "❌ Этот пользователь уже является модератором данного топика."

        role_id = db.get_role_id("moderator")
        if role_id == 0:
            return False, "❌ Роль 'moderator' не найдена в БД."

        if db.grant_role(target_user_id, role_id, topic_id):
            return True, "✅ Пользователь назначен модератором топика."
        return False, "❌ Не удалось назначить модератора."

    @staticmethod
    def assign_moderator_role(user_input: str, topic_id: int) -> tuple[bool, str]:
        """Логика назначения пользователя модератором топика (через ввод)."""
        target_user_id, err = ManagementService._parse_and_validate_id(user_input)
        if err: return False, err
        if not db.user_exists(target_user_id):
            return False, "❌ Пользователь с таким ID не найден в системе."
        return ManagementService.assign_moderator_role_by_id(target_user_id, topic_id)

    @staticmethod
    def grant_direct_access_by_id(target_user_id: int, topic_id: int) -> tuple[bool, str]:
        """Прямая выдача доступа по ID."""
        if db.grant_direct_access(target_user_id, topic_id):
            return True, "✅ Прямой доступ выдан."
        return False, "❌ Ошибка: Доступ уже есть или сбой БД."

    @staticmethod
    def grant_direct_access(user_input: str, topic_id: int) -> tuple[bool, str]:
        """Логика выдачи прямого доступа к топику (через ввод)."""
        target_user_id, err = ManagementService._parse_and_validate_id(user_input)
        if err: return False, err
        if not db.user_exists(target_user_id):
            return False, "❌ Пользователь не найден в системе."
        return ManagementService.grant_direct_access_by_id(target_user_id, topic_id)

    @staticmethod
    def revoke_direct_access(user_id: int, topic_id: int) -> tuple[bool, str]:
        """Отзывает прямой доступ пользователя к топику."""
        db.revoke_direct_access(user_id, topic_id)
        logger.info(f"🚫 Прямой доступ пользователя {user_id} к топику {topic_id} отозван.")
        return True, "✅ Прямой доступ отозван."

    @staticmethod
    def update_user_name(user_id: int, first_name: str, last_name: str) -> tuple[bool, str]:
        """Обновляет имя пользователя с валидацией и экранированием."""
        first_name, last_name = html.escape(first_name.strip()), html.escape(last_name.strip())
        if not first_name:
            return False, "❌ Имя не может быть пустым."
            
        if len(first_name) > ManagementService.MAX_NAME_LENGTH or len(last_name) > ManagementService.MAX_NAME_LENGTH:
            return False, f"❌ Максимум {ManagementService.MAX_NAME_LENGTH} символов."
            
        db.update_user_name(user_id, first_name, last_name)
        return True, "✅ Данные пользователя обновлены."

    @staticmethod
    def update_topic_name(topic_id: int, new_name: str) -> tuple[bool, str]:
        """Обновляет название топика."""
        new_name = html.escape(new_name.strip())
        if not new_name:
            return False, "❌ Название не может быть пустым."
        if len(new_name) > ManagementService.MAX_NAME_LENGTH:
            return False, "❌ Название слишком длинное."
            
        db.update_topic_name(topic_id, new_name)
        return True, "✅ Название топика обновлено."

    @staticmethod
    def handle_external_topic_deletion(topic_id: int):
        """
        [CC-1, CC-2] Реагирует на внешнее удаление топика в Telegram.
        Удаляет топик из БД и все связанные анонсы.
        """
        logger.warning(f"🗑 [SYNC] Обнаружено внешнее удаление топика {topic_id}. Синхронизация БД...")
        db.delete_announcements_by_topic(topic_id)
        db.delete_topic(topic_id)
        ManagementService._trigger_sheets_sync("all")

    @staticmethod
    def add_topic_to_group(group_id: int, topic_id: int) -> tuple[bool, str]:
        """Привязывает топик к группе."""
        if db.add_topic_to_group(group_id, topic_id):
            return True, "✅ Топик привязан к группе."
        return False, "❌ Не удалось привязать топик (возможно, уже привязан)."

    @staticmethod
    def grant_role(user_id: int, role_id: int, topic_id: int = None) -> tuple[bool, str]:
        """Выдает роль пользователю."""
        if db.grant_role(user_id, role_id, topic_id):
            return True, "✅ Роль назначена."
        return False, "❌ Ошибка (возможно, роль уже назначена)."

    @staticmethod
    def search_entities(s_type: str, query: str) -> list:
        """Централизованный диспетчер поиска по типам сущностей (обертка для UI)."""
        if s_type == "user":
            return [(u[0], f"{u[1]} {u[2]}") for u in db.find_users_by_query(query)]
        elif s_type == "group":
            return db.find_groups_by_query(query)
        elif s_type == "topic":
            return db.find_topics_by_query(query)
        return []

    @staticmethod
    def get_entity_name(entity_type: str, entity_id: int) -> str:
        """Возвращает название сущности для вывода в UI."""
        logger.debug(f"🔍 Определение имени сущности: {entity_type} (ID: {entity_id})")
        if entity_type == "group":
            return db.get_group_name(entity_id) or f"Группа {entity_id}"
        elif entity_type == "topic":
            return db.get_topic_name(entity_id) or f"Топик {entity_id}"
        elif entity_type == "user":
            return db.get_user_name(entity_id) or f"Пользователь {entity_id}"
        elif entity_type in ["event", "event_approval", "event_participation"]:
            event = db.get_event_details(entity_id)
            return event["title"] if event else f"Мероприятие {entity_id}"
        return "Неизвестный объект"

    @staticmethod
    def execute_deletion(action: str, target_id: int, extra_id: int = 0) -> tuple[bool, str, str]:
        """
        Выполняет удаление и возвращает (успех, сообщение, следующий_колбэк).
        Следующий колбэк указывает, какое меню показать после успеха.
        """
        if action == "group_del":
            db.delete_group(target_id)
            ManagementService._trigger_sheets_sync("all")
            return True, "✅ Группа удалена", "manage_groups"
            
        elif action in ["topic_del", "mod_topic_del"]:
            # target_id — топик, extra_id — группа
            db.remove_topic_from_group(extra_id, target_id)
            ManagementService._trigger_sheets_sync("all")
            
            if action == "mod_topic_del":
                 return True, "✅ Топик убран из группы", f"mod_topic_groups_{target_id}"
            return True, "✅ Топик убран из группы", f"group_topics_list_{extra_id}"
            
        elif action == "global_topic_del":
            db.delete_topic(target_id)
            ManagementService._trigger_sheets_sync("all")
            return True, "✅ Топик полностью удален", "all_topics_list"
            
        elif action == "user_del":
            db.delete_user(target_id)
            ManagementService._trigger_sheets_sync("all")
            return True, "✅ Пользователь удален", "manage_users"

        elif action.startswith("role_rev"):
            # Отзыв любой роли (админ)
            role_id = int(action.split("_")[-1]) if action != "role_rev" else 0
            t_id = None if extra_id == 0 else extra_id
            db.revoke_role(target_id, role_id, t_id)
            return True, "✅ Роль отозвана", f"user_roles_manage_{target_id}"

        elif action == "mod_rem":
            # Снятие модератора (вызывается модератором)
            role_id = db.get_role_id("moderator")
            db.revoke_role(target_id, role_id, extra_id)
            return True, "✅ Модератор удалён", f"mod_topic_moderators_{extra_id}"

        elif action == "event_del":
            db.delete_event(target_id)
            ManagementService._trigger_sheets_sync("all")
            return True, "✅ Мероприятие удалено", "event_list"

        return False, "❌ Ошибка: неизвестное действие", "admin_main"
    
    @staticmethod
    async def sync_from_sheets() -> tuple[bool, str]:
        """Синхронизирует локальную БД данными из Google Sheets (Manual Import)."""
        from services.google_sheets_service import GoogleSheetsService
        
        users_data = await GoogleSheetsService.import_users()
        if not users_data:
            return False, "❌ Ошибка: Данные пользователей не получены или лист пуст."
            
        # Оптимизация: получаем текущих юзеров для сравнения [PL-HI]
        current_users = {u[0]: (u[1], u[2]) for u in db.get_all_users()}
        
        imported_count = 0
        updated_count = 0
        for row in users_data:
            u_id = row.get("User ID")
            f_name = str(row.get("First Name", ""))
            l_name = str(row.get("Last Name", ""))
            
            if u_id and f_name:
                try:
                    u_id_int = int(u_id)
                    if u_id_int not in current_users:
                        # Новый пользователь
                        db.add_user(u_id_int, f_name, l_name)
                        imported_count += 1
                    else:
                        # Проверяем, изменилось ли имя
                        old_f, old_l = current_users[u_id_int]
                        if f_name != old_f or l_name != old_l:
                            db.update_user_name(u_id_int, f_name, l_name)
                            updated_count += 1
                except Exception as e:
                    logger.warning(f"Ошибка парсинга строки при импорте: {row} ({e})")
        
        status = f"✅ Синхронизировано. Новых: {imported_count}, Обновлено: {updated_count}"
        return True, status

    @staticmethod
    def _trigger_sheets_sync(mode: str = "all", entity_id: int = None):
        """Запускает синхронизацию с Google Sheets в фоновом режиме."""
        import asyncio
        from services.google_sheets_service import GoogleSheetsService
        from services.event_service import EventService
        
        async def _task():
            try:
                if mode in ["all", "users"]:
                    users = db.get_all_users()
                    users_with_roles = []
                    for u in users:
                        roles = db.get_user_roles(u[0])
                        roles_str = ", ".join([f"{r[0]}({r[1]})" if r[1] else r[0] for r in roles])
                        users_with_roles.append((u[0], u[1], u[2], roles_str))
                    await GoogleSheetsService.export_users(users_with_roles)
                
                if mode in ["all", "groups"]:
                    groups = db.get_all_groups()
                    groups_data = []
                    for g_id, g_name in groups:
                        topics = db.get_topics_of_group(g_id)
                        topics_str_list = [str(t) for t in topics]
                        groups_data.append({'id': g_id, 'name': g_name, 'topics': topics_str_list})
                    await GoogleSheetsService.export_groups(groups_data)

                if mode in ["all", "events"]:
                    events = db.get_active_events()
                    events_data = []
                    for e in events:
                        # Получаем детали с участниками [PL-HI]
                        details = EventService.get_event_details(e['event_id'])
                        events_data.append(details)
                    await GoogleSheetsService.export_events(events_data)

                if mode == "event_participants" and entity_id:
                    details = EventService.get_event_details(entity_id)
                    if details:
                        # Разрешаем имена участников для экспорта
                        p_ids = details['participants']
                        l_ids = set(details['leads'])
                        names = db.get_user_names_by_ids(p_ids)
                        
                        full_participants = []
                        for p_id in p_ids:
                            full_participants.append({
                                'user_id': p_id,
                                'name': names.get(p_id, f"ID:{p_id}"),
                                'role': "Организатор" if p_id in l_ids else "Участник",
                                'join_date': "" # В БД пока нет даты вступления
                            })
                            
                        await GoogleSheetsService.export_event_participants(
                            entity_id, details['title'], full_participants
                        )
            except Exception as e:
                logger.error(f"Фоновая синхронизация Google Sheets провалилась ({mode}): {e}")

        asyncio.create_task(_task())

    # --- НОВЫЕ ОПЕРАЦИИ ШАБЛОНОВ (ЭТАП 2) ---

    @staticmethod
    def toggle_user_group_template(user_id: int, group_id: int) -> tuple[bool, str]:
        """Управляет членством пользователя в ШАБЛОНЕ группы."""
        members = set(db.get_group_template_members(group_id))
        if user_id in members:
            db.remove_from_group_template(group_id, user_id)
            return True, "🗑 Пользователь удален из шаблона."
        else:
            db.add_to_group_template(group_id, user_id)
            return True, "📋 Пользователь добавлен в шаблон."

    @staticmethod
    def apply_group_to_topic(group_id: int, topic_id: int) -> tuple[bool, str]:
        """Применяет шаблон группы к топику (добавление новых)."""
        user_ids = db.get_group_template_members(group_id)
        if not user_ids:
            return False, "⚠️ Шаблон группы пуст."
        
        if db.grant_direct_access_bulk(user_ids, topic_id):
            return True, f"✅ Шаблон применен! Добавлено {len(user_ids)} чел."
        return False, "❌ Ошибка при применении шаблона."

    @staticmethod
    def sync_group_to_topic(group_id: int, topic_id: int) -> tuple[bool, str]:
        """Синхронизирует топик с шаблоном (полная перезапись прав)."""
        user_ids = db.get_group_template_members(group_id)
        # Очищаем старый доступ
        db.revoke_all_direct_access(topic_id)
        
        if not user_ids:
            return True, "✅ Доступ очищен (шаблон пуст)."

        if db.grant_direct_access_bulk(user_ids, topic_id):
            return True, f"✅ Синхронизация завершена! Доступно {len(user_ids)} чел."
        return False, "❌ Ошибка при синхронизации."

    @staticmethod
    def copy_topic_to_topic(source_topic_id: int, target_topic_id: int) -> tuple[bool, str]:
        """Копирует права доступа из одного топика в другой."""
        users = db.get_direct_access_users(source_topic_id)
        if not users:
            return False, "⚠️ Исходный топик не имеет прямого доступа."
        
        user_ids = [u[0] for u in users]
        if db.grant_direct_access_bulk(user_ids, target_topic_id):
            return True, f"✅ Права скопированы ({len(user_ids)} чел.)."
        return False, "❌ Ошибка при копировании прав."

    # --- МЕРОПРИЯТИЯ (EXPEDITION PROTOCOL) ---

    @staticmethod
    def create_event_action(title: str, start_date: str, creator_id: int, is_approved: int = 0) -> int:
        """
        Бизнес-логика создания мероприятия [PL-6.7]: 
        санитизация ввода и регистрация автора как лидера.
        """
        title = html.escape(title.strip())[:100]
        start_date = html.escape(start_date.strip())[:100]
        
        event_id = db.create_event(title, start_date, "", creator_id, is_approved)
        if event_id > 0:
            db.add_event_participant(event_id, creator_id)
            db.add_event_lead(event_id, creator_id)
        return event_id

    @staticmethod
    def add_event_participation_action(event_id: int, user_id: int) -> str:
        """Логика записи на мероприятие с текстовым статусом."""
        if db.is_event_participant(event_id, user_id):
            return "Вы уже записаны!"
        
        db.add_event_participant(event_id, user_id)
        ManagementService._trigger_sheets_sync("event_participants", event_id)
        return "Вы записаны!"

    @staticmethod
    def remove_event_participation_action(event_id: int, user_id: int) -> str:
        """Логика отписки от мероприятия с текстовым статусом."""
        if not db.is_event_participant(event_id, user_id):
            return "Вы еще не записались чтобы не идти!"
        
        db.remove_event_participant(event_id, user_id)
        ManagementService._trigger_sheets_sync("event_participants", event_id)
        return "Ваша запись отменена!"

    @staticmethod
    def toggle_event_participation(event_id: int, user_id: int) -> tuple[bool, str]:
        """Логика записи/отписки от мероприятия."""
        if db.is_event_participant(event_id, user_id):
            db.remove_event_participant(event_id, user_id)
            ManagementService._trigger_sheets_sync("event_participants", event_id)
            return True, "❌ Вы больше не участвуете."
        else:
            db.add_event_participant(event_id, user_id)
            ManagementService._trigger_sheets_sync("event_participants", event_id)
            return True, "✅ Вы записаны!"

    @staticmethod
    def approve_event_action(event_id: int) -> bool:
        """Одобрение мероприятия администратором."""
        return db.approve_event(event_id)

    @staticmethod
    def submit_request(user_id: int, entity_type: str, entity_id: int) -> int:
        """
        Создает заявку на аудит. Если заявка уже существует, возвращает её ID.
        """
        existing = db.get_user_pending_request(user_id, entity_type, entity_id)
        if existing:
            return existing
        return db.create_audit_request(user_id, entity_type, entity_id)

    @staticmethod
    def get_pending_request_id(entity_type: str, entity_id: int) -> Optional[int]:
        """Возвращает ID первой активной заявки для сущности."""
        requests = db.get_pending_requests_by_type(entity_type, entity_id)
        return requests[0] if requests else None

    @staticmethod
    def get_user_pending_request_id(user_id: int, entity_type: str, entity_id: int) -> Optional[int]:
        """Возвращает ID активной заявки конкретного пользователя."""
        return db.get_user_pending_request(user_id, entity_type, entity_id)

    @staticmethod
    async def resolve_request(bot: Bot, request_id: int, status: str, comment: str = None) -> tuple[bool, str]:
        """
        Разрешает заявку (одобрено/отклонено), выполняет действие в БД и уведомляет пользователя.
        Идемпотентен: проверяет текущий статус перед выполнением.
        """
        request = db.get_audit_request(request_id)
        if not request:
            return False, "❌ Заявка не найдена."

        # Проверка на повторное решение [CC-2]
        if request["status"] != "pending":
            logger.warning(f"⚠️ Попытка повторного решения заявки {request_id} (Текущий статус: {request['status']})")
            return False, f"⚠️ Эта заявка уже была обработана ({request['status']})."

        logger.info(f"🛡 [AUDIT] Резолв заявки {request_id}: {status} (Тип: {request['entity_type']}, ID: {request['entity_id']})")

        if not db.resolve_audit_request(request_id, status, comment):
            return False, "❌ Ошибка при обновлении статуса в БД."

        # Выполняем действие в БД в зависимости от статуса [CC-1]
        if status == "approved":
            if request["entity_type"] == "event_approval":
                db.approve_event(request["entity_id"])
                ManagementService._trigger_sheets_sync("events")
            elif request["entity_type"] == "event_participation":
                db.add_event_participant(request["entity_id"], request["user_id"])
                ManagementService._trigger_sheets_sync("event_participants", request["entity_id"])
        
        elif status == "rejected":
            if request["entity_type"] == "event_approval":
                # Если отклонили создание мероприятия — удаляем черновик [CC-1]
                db.delete_event(request["entity_id"])
                logger.info(f"🗑 Мероприятие {request['entity_id']} удалено из-за отклонения заявки.")

        # Формируем человекочитаемое уведомление [CC-2]
        entity_name = ManagementService.get_entity_name(request["entity_type"], request["entity_id"])
        status_icon = "✅" if status == "approved" else "❌"
        is_approved = status == "approved"

        # Маппинг названий и окончаний в зависимости от рода
        naming_map = {
            "event_approval": ("Ваше мероприятие", "одобрено", "отклонено"),
            "event_participation": ("Ваша запись на мероприятие", "одобрена", "отклонена"),
            "group": ("Ваша группа", "одобрена", "отклонена"),
            "topic": ("Ваш топик", "одобрен", "отклонен"),
            "user": ("Пользователь", "одобрен", "отклонен")
        }
        
        prefix, ok_text, fail_text = naming_map.get(
            request["entity_type"], 
            ("Ваша заявка по объекту", "одобрена", "отклонена")
        )
        
        res_text = ok_text if is_approved else fail_text
        notify_text = f"{status_icon} {prefix} <b>{entity_name}</b> {res_text}.\n"
        
        if comment:
            notify_text += f"💬 Комментарий: <i>{comment}</i>"

        await NotificationService.send_to_users(bot, [request["user_id"]], notify_text)
        
        return True, f"✅ Заявка {request_id} разрешена ({res_text})."
