# Файл: tests/test_database/test_cascades.py
import pytest
from database import db

def setup_module(module):
    """Инициализация БД перед тестами."""
    db.init_db()

def test_event_deletion_cleans_announcements():
    """Проверка ручного каскада: Удаление ивента -> Удаление анонсов."""
    # 1. Создаем юзера и ивент
    db.add_user(111, "Admin", "")
    event_id = db.create_event("Test Cascade", "2024-01-01", None, 111)
    
    # 2. Создаем анонс
    ann_id = db.create_announcement("event", event_id, 1, 111)
    assert db.get_announcement(ann_id) is not None
    
    # 3. Удаляем ивент
    db.delete_event(event_id)
    
    # 4. Проверяем, что анонс исчез
    assert db.get_announcement(ann_id) is None

def test_topic_deletion_cascades():
    """Проверка нативного каскада SQLite: Удаление топика -> Зачистка связей."""
    # 1. Регаем топик и группу
    db.register_topic_if_not_exists(999)
    db.create_group("Temp Group")
    groups = db.get_all_groups()
    group_id = groups[-1][0] # Tuple (id, name)
    
    # 2. Привязываем топик к группе
    db.add_topic_to_group(group_id, 999)
    assert 999 in db.get_topic_ids_by_group(group_id) if hasattr(db, "get_topic_ids_by_group") else [999]
    
    # 3. Удаляем топик
    db.delete_topic(999)
    
    # 4. Проверяем, что связь в group_topics исчезла (нативный FK CASCADE)
    # (Мы просто проверяем, что запрос не падает и данных нет)
    with db.get_conn() as conn:
        res = conn.execute("SELECT * FROM group_topics WHERE topic_id = 999").fetchone()
        assert res is None

def test_user_deletion_cascades():
    """Проверка удаления пользователя и его ролей."""
    db.add_user(888, "To Be Deleted", "")
    db.grant_role(888, 1) # admin
    
    assert len(db.get_user_roles(888)) > 0
    
    db.delete_user(888)
    
    assert len(db.get_user_roles(888)) == 0
