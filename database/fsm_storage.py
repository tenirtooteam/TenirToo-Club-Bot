# Файл: database/fsm_storage.py
"""
[Feature 012 / №16] Персистентный FSM-storage поверх общего SQLite-соединения.

Реализация aiogram `BaseStorage`, переживающая рестарт процесса: состояние и
данные FSM живут в таблице `fsm_storage` (см. database/connection.py::init_db),
а не в памяти процесса, как у штатного `MemoryStorage`.

Ключевые инварианты (полный контракт — specs/012-persistent-fsm-storage/):
- I-1: thread_id=None отображается в сентинел 0 — SQLite считает NULL в составном
  PK различными, что дало бы дубли на основном пути (личные сообщения).
- I-4: строка удаляется ТОЛЬКО при пустом состоянии И пустых данных
  одновременно. Удаление по одному лишь снятому состоянию стёрло бы трекинг-ключи
  стерильного интерфейса (last_menu_ids и пр.) — это нарушение R-FSM-1.
- Соединение берётся исключительно через get_conn(); своего соединения storage не
  открывает и на close() не закрывает (им владеет database/connection.py).
- Конструктор не касается БД: loader.py создаёт storage на импорте, а init_db()
  отрабатывает позже.
"""
import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from .connection import get_conn

logger = logging.getLogger(__name__)

_EMPTY_DATA = "{}"


def _pk(key: StorageKey) -> tuple:
    """StorageKey -> кортеж столбцов PK. thread_id=None -> сентинел 0 (I-1)."""
    return (
        key.bot_id,
        key.chat_id,
        key.user_id,
        key.thread_id or 0,
        key.destiny,
    )


_WHERE = (
    "bot_id = ? AND chat_id = ? AND user_id = ? "
    "AND thread_id = ? AND destiny = ?"
)


class SQLiteStorage(BaseStorage):
    """Персистентный storage FSM на общем SQLite-соединении проекта."""

    @staticmethod
    def _prune(conn, pk: tuple) -> None:
        """I-4: убрать строку, если и состояние снято, и данные пусты."""
        conn.execute(
            f"DELETE FROM fsm_storage WHERE {_WHERE} "
            f"AND state IS NULL AND data = '{_EMPTY_DATA}'",
            pk,
        )

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        resolved = state.state if isinstance(state, State) else state
        pk = _pk(key)
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO fsm_storage "
                    "(bot_id, chat_id, user_id, thread_id, destiny, state, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(bot_id, chat_id, user_id, thread_id, destiny) "
                    "DO UPDATE SET state = excluded.state, updated_at = CURRENT_TIMESTAMP",
                    (*pk, resolved),
                )
                self._prune(conn, pk)

    async def get_state(self, key: StorageKey) -> Optional[str]:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT state FROM fsm_storage WHERE {_WHERE}", _pk(key)
            ).fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        # Сериализация ДО открытия транзакции: несериализуемое значение обязано
        # всплыть громко (D-3), а не молча потерять состояние.
        payload = json.dumps(data)
        pk = _pk(key)
        with get_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT INTO fsm_storage "
                    "(bot_id, chat_id, user_id, thread_id, destiny, data, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(bot_id, chat_id, user_id, thread_id, destiny) "
                    "DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP",
                    (*pk, payload),
                )
                self._prune(conn, pk)

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT data FROM fsm_storage WHERE {_WHERE}", _pk(key)
            ).fetchone()
        if not row or row[0] is None:
            return {}
        try:
            return json.loads(row[0])
        except (ValueError, TypeError):
            # FR-009: битая запись трактуется как отсутствие данных, факт логируется,
            # обработка события не падает и строка не удаляется автоматически.
            logger.warning(
                "Повреждённые данные FSM для ключа %s — трактую как пустые.", _pk(key)
            )
            return {}

    async def close(self) -> None:
        # No-op (D-5): общим соединением владеет database/connection.py; закрыть его
        # здесь значило бы выдернуть соединение из-под остального кода в том же
        # процессе (включая FastAPI-часть).
        pass
