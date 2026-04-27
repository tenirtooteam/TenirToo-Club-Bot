import gspread_asyncio
from google.oauth2.service_account import Credentials
import config
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    _agcm = None

    @staticmethod
    def get_creds():
        """Создает учетные данные из файла."""
        if not os.path.exists(config.GOOGLE_CREDS_PATH):
            raise FileNotFoundError(f"Файл учетных данных Google не найден: {config.GOOGLE_CREDS_PATH}")
            
        return Credentials.from_service_account_file(
            config.GOOGLE_CREDS_PATH,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )

    @classmethod
    async def get_client(cls):
        """Возвращает асинхронный клиент gspread."""
        if cls._agcm is None:
            cls._agcm = gspread_asyncio.AsyncioGspreadClientManager(cls.get_creds)
        return await cls._agcm.authorize()

    @staticmethod
    async def export_users(users: List[tuple]):
        """
        Выгружает список пользователей в лист 'Users'.
        users: список кортежей (id, first_name, last_name, roles_str)
        """
        if not config.SPREADSHEET_ID:
            logger.warning("SPREADSHEET_ID не задан. Экспорт отменен.")
            return False
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            
            # Пытаемся найти или создать лист
            try:
                worksheet = await sh.worksheet("Users")
            except Exception:
                worksheet = await sh.add_worksheet(title="Users", rows="1000", cols="5")
                
            # Заголовки
            headers = ["User ID", "First Name", "Last Name", "Roles"]
            data = [headers]
            for u in users:
                data.append([str(u[0]), u[1], u[2] or "", u[3]])
                
            await worksheet.clear()
            await worksheet.update(range_name="A1", values=data)
            logger.info(f"Экспортировано {len(users)} пользователей в Google Sheets.")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта пользователей в Google Sheets: {e}")
            return False

    @staticmethod
    async def export_groups(groups_data: List[Dict[str, Any]]):
        """
        Выгружает группы и их топики в лист 'Groups'.
        groups_data: список словарей {'id': int, 'name': str, 'topics': List[str]}
        """
        if not config.SPREADSHEET_ID:
            return False
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            
            try:
                worksheet = await sh.worksheet("Groups")
            except Exception:
                worksheet = await sh.add_worksheet(title="Groups", rows="1000", cols="5")
                
            headers = ["Group ID", "Group Name", "Topics"]
            data = [headers]
            for g in groups_data:
                topics_str = ", ".join(map(str, g['topics']))
                data.append([str(g['id']), g['name'], topics_str])
                
            await worksheet.clear()
            await worksheet.update(range_name="A1", values=data)
            logger.info(f"Экспортировано {len(groups_data)} групп в Google Sheets.")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта групп в Google Sheets: {e}")
            return False

    @staticmethod
    async def import_users():
        """Читает пользователей из листа 'Users' и возвращает список словарей."""
        if not config.SPREADSHEET_ID:
            return []
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            worksheet = await sh.worksheet("Users")
            return await worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Ошибка импорта пользователей из Google Sheets: {e}")
            return []

    @staticmethod
    async def import_groups():
        """Читает группы из листа 'Groups'."""
        if not config.SPREADSHEET_ID:
            return []
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            worksheet = await sh.worksheet("Groups")
            return await worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Ошибка импорта групп из Google Sheets: {e}")
            return []
    @staticmethod
    async def export_events(events: List[Dict[str, Any]]):
        """
        Выгружает сводный список мероприятий в лист 'Events'.
        events: список словарей с данными из БД.
        """
        if not config.SPREADSHEET_ID:
            return False
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            
            try:
                worksheet = await sh.worksheet("Events")
            except Exception:
                worksheet = await sh.add_worksheet(title="Events", rows="1000", cols="10")
                
            headers = ["ID", "Title", "Date (Text)", "Start ISO", "End ISO", "Status", "Participants Count"]
            data = [headers]
            for e in events:
                data.append([
                    str(e['event_id']), 
                    e['title'], 
                    e['start_date'], 
                    e.get('start_iso', ""), 
                    e.get('end_iso', ""),
                    "Approved" if e['is_approved'] else "Pending",
                    str(len(e.get('participants', [])))
                ])
                
            await worksheet.clear()
            await worksheet.update(range_name="A1", values=data)
            logger.info(f"Экспортировано {len(events)} мероприятий в Google Sheets.")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта мероприятий в Google Sheets: {e}")
            return False

    @staticmethod
    async def export_event_participants(event_id: int, title: str, participants: List[Dict[str, Any]]):
        """
        Выгружает список участников конкретного похода в отдельный лист.
        title: Название похода (используется для имени листа).
        """
        if not config.SPREADSHEET_ID:
            return False
            
        try:
            client = await GoogleSheetsService.get_client()
            sh = await client.open_by_key(config.SPREADSHEET_ID)
            
            # Имя листа: "E_ID_Title" (ограничение длины 31 символ в Google Sheets)
            sheet_title = f"E_{event_id}_{title}"[:30]
            
            try:
                worksheet = await sh.worksheet(sheet_title)
            except Exception:
                worksheet = await sh.add_worksheet(title=sheet_title, rows="500", cols="5")
                
            headers = ["User ID", "Name", "Role", "Join Date"]
            data = [headers]
            for p in participants:
                data.append([
                    str(p['user_id']), 
                    p['name'], 
                    p['role'], 
                    p.get('join_date', "")
                ])
                
            await worksheet.clear()
            await worksheet.update(range_name="A1", values=data)
            logger.info(f"Экспортировано {len(participants)} участников ивента {event_id} в Google Sheets.")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта участников ивента {event_id} в Google Sheets: {e}")
            return False
