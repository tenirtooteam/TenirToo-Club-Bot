import pytest
from database import db

def test_user_management_integrity(db_setup):
    """Проверка целостности управления пользователями."""
    user_id = 111
    
    # 1. Добавление
    db.add_user(user_id, "Ivan", "Ivanov")
    assert db.user_exists(user_id)
    assert db.get_user_name(user_id) == "Ivan Ivanov"
    
    # 2. Поиск
    results = db.find_users_by_query("ivan")
    assert len(results) == 1
    assert results[0][0] == user_id
    
    # 3. Обновление
    db.update_user_name(user_id, "Petr", "Petrov")
    assert db.get_user_name(user_id) == "Petr Petrov"
    
    # 4. Удаление
    db.delete_user(user_id)
    assert not db.user_exists(user_id)

def test_group_topic_cascade_integrity(db_setup):
    """Проверка каскадного удаления групп и топиков [PL-2.2.44]."""
    group_name = "Cascade Group"
    topic_id = 222
    
    # 1. Создаем группу и топик
    db.create_group(group_name)
    db.register_topic_if_not_exists(topic_id)
    groups = db.find_groups_by_query(group_name)
    group_id = groups[0][0]
    
    # 2. Связываем
    db.add_topic_to_group(group_id, topic_id)
    assert topic_id in db.get_topics_of_group(group_id)
    
    # 3. Удаляем группу
    db.delete_group(group_id)
    
    # 4. ПРОВЕРКА: Связь должна исчезнуть каскадно
    # Но топик сам должен остаться (он независимая сущность)
    assert db.get_topic_name(topic_id) is not None
    # А в связях групп его быть не должно
    assert len(db.get_groups_by_topic(topic_id)) == 0

def test_event_lead_cascade(db_setup):
    """Проверка каскадного удаления лидеров при удалении мероприятия."""
    user_id = 333
    db.add_user(user_id, "Lead", "User")
    
    event_id = db.create_event("Hike", "2026-05-01", None, user_id)
    db.add_event_lead(event_id, user_id)
    
    # Удаляем ивент
    db.delete_event(event_id)
    
    # Проверяем, что в event_leads пусто
    with db.get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM event_leads WHERE event_id = ?", (event_id,)).fetchone()[0]
        assert count == 0
