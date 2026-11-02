import json
from plugins._base import PluginBase


class JsonFormatterPlugin(PluginBase):
    NAME = "json_formatter"
    VERSION = "1.0"
    DESCRIPTION = "Форматирует JSON с отступами и проверяет корректность JSON-строки."
    AUTHOR = "look-afk"
    COMMANDS = {
        "json_format": "Красиво форматировать JSON: json_format <JSON>",
        "json_validate": "Проверить JSON без изменения данных: json_validate <JSON>",
    }

    async def handle(self, cmd: str, param: str) -> str:
        if not param.strip():
            return "Передай JSON после команды. Пример: json_format {\"ok\":true,\"items\":[1,2]}"
        try:
            value = json.loads(param)
        except json.JSONDecodeError as exc:
            return f"Ошибка JSON: {exc.msg} (строка {exc.lineno}, столбец {exc.colno})"
        if cmd == "json_validate":
            return "JSON корректен."
        return json.dumps(value, ensure_ascii=False, indent=2)
