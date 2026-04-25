from typing import Dict

class HelpService:
    """
    Centralized registry for help content and tooltips.
    Decouples help text from UI handlers for better scalability and localization.
    """
    
    # [CC-2] Content Registry: All help strings must reside here.
    HELP_CONTENT: Dict[str, str] = {
        "templates": (
            "<b>ℹ️ О шаблонах групп</b>\n\n"
            "Шаблоны — это инструменты для массового управления доступом. "
            "Вы добавляете пользователей в шаблон, а затем кнопкой <b>«Синхронизировать»</b> "
            "копируете весь список в конкретный топик.\n\n"
            "⚠️ <b>Важно:</b> Изменение состава шаблона НЕ меняет доступ в топиках автоматически. "
            "Для обновления доступа нужно нажать кнопку синхронизации в меню управления топиком."
        ),
        "help_general": (
            "🤖 <b>Информационный гид Tenir-Too Bot</b>\n\n"
            "<b>Команды:</b>\n"
            "🔹 /start : Главное меню\n"
            "🔹 /help  : Вызов этой справки\n\n"
            "<i>Бот работает в скрытом режиме: сообщения от неавторизованных пользователей удаляются автоматически.</i>"
        ),
    }

    @staticmethod
    def get_help(key: str) -> str:
        """
        Retrieves help text by key. Returns a fallback message if key is missing.
        """
        return HelpService.HELP_CONTENT.get(
            key, 
            "<i>⚠️ Справочная информация для данного раздела пока не добавлена.</i>"
        )
