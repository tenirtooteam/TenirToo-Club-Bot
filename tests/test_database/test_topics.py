import pytest
from database import topics

def test_topic_registration_and_naming():
    topic_id = 123
    # Авторегистрация
    topics.register_topic_if_not_exists(topic_id)
    assert topics.get_topic_name(topic_id) == f"Топик {topic_id}"
    
    # Обновление имени
    topics.update_topic_name(topic_id, "New Topic Name")
    assert topics.get_topic_name(topic_id) == "New Topic Name"
    
    # Проверка General
    topics.register_topic_if_not_exists(-1)
    assert topics.get_topic_name(-1) == "General"

def test_get_all_unique_topics():
    topics.update_topic_name(1, "Beta")
    topics.update_topic_name(2, "Alpha")
    
    all_ids = topics.get_all_unique_topics()
    # Должно вернуть список ID, отсортированный по имени (Alpha=2, Beta=1)
    assert all_ids == [2, 1]

def test_delete_topic():
    topic_id = 456
    topics.update_topic_name(topic_id, "Temp")
    assert topic_id in topics.get_all_unique_topics()
    
    topics.delete_topic(topic_id)
    assert topic_id not in topics.get_all_unique_topics()

def test_find_topics_by_query():
    topics.update_topic_name(10, "Курилка")
    topics.update_topic_name(11, "Разработка")
    topics.update_topic_name(12, "Админка")
    
    res = topics.find_topics_by_query("раб")
    assert len(res) == 1
    assert res[0][0] == 11
    
    res = topics.find_topics_by_query("ка")
    assert len(res) == 3 # КурилКА, РазработКА, АдминКА
