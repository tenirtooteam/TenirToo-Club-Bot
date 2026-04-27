# Файл: database/announcements.py
import sqlite3
from datetime import datetime
from database.connection import get_conn

def create_announcement(a_type: str, target_id: int, topic_id: int, creator_id: int, chat_id: int = None, message_id: int = None) -> int:
    """Создает запись об анонсе и возвращает его ID."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO announcements (type, target_id, topic_id, creator_id, chat_id, message_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (a_type, target_id, topic_id, creator_id, chat_id, message_id))
        ann_id = cursor.lastrowid
        conn.commit()
    return ann_id

def get_announcement(ann_id: int):
    """Возвращает данные анонса по ID."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM announcements WHERE id = ?', (ann_id,))
        res = cursor.fetchone()
    return res

def delete_announcements_by_target(a_type: str, target_id: int):
    """Удаляет анонсы при удалении родительской сущности."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM announcements WHERE type = ? AND target_id = ?', (a_type, target_id))
        conn.commit()

def delete_announcements_by_topic(topic_id: int):
    """Удаляет все анонсы, привязанные к топику."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM announcements WHERE topic_id = ?', (topic_id,))
        conn.commit()

def update_announcement_metadata(ann_id: int, chat_id: int, message_id: int):
    """Привязывает запись анонса к конкретному сообщению в Telegram."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE announcements SET chat_id = ?, message_id = ? WHERE id = ?', (chat_id, message_id, ann_id))
        conn.commit()
