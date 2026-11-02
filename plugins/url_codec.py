from urllib.parse import quote, unquote
from plugins._base import PluginBase


class UrlCodecPlugin(PluginBase):
    NAME = "url_codec"
    VERSION = "1.0"
    DESCRIPTION = "Кодирует и декодирует URL-компоненты, включая пробелы и кириллицу."
    AUTHOR = "look-afk"
    COMMANDS = {
        "url_encode": "URL-кодирование текста: url_encode <текст>",
        "url_decode": "Декодирование URL-текста: url_decode <строка>",
    }

    async def handle(self, cmd: str, param: str) -> str:
        if not param:
            return "Добавь текст после команды."
        if cmd == "url_encode":
            return quote(param, safe="")
        if cmd == "url_decode":
            return unquote(param)
        return "Неизвестная команда."
