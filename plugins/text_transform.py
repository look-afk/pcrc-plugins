import re
from plugins._base import PluginBase


class TextTransformPlugin(PluginBase):
    NAME = "text_transform"
    VERSION = "1.0"
    DESCRIPTION = "Меняет регистр текста и создаёт URL-friendly slug."
    AUTHOR = "look-afk"
    COMMANDS = {
        "text_upper": "Преобразовать текст в верхний регистр.",
        "text_lower": "Преобразовать текст в нижний регистр.",
        "text_title": "Преобразовать слова в Title Case.",
        "text_slug": "Создать slug из текста для URL.",
    }

    async def handle(self, cmd: str, param: str) -> str:
        if not param:
            return "Передай текст после команды."
        if cmd == "text_upper":
            return param.upper()
        if cmd == "text_lower":
            return param.lower()
        if cmd == "text_title":
            return param.title()
        if cmd == "text_slug":
            text = param.lower().strip()
            text = re.sub(r"[^a-z0-9а-яё]+", "-", text, flags=re.IGNORECASE)
            return text.strip("-")
        return "Неизвестная команда."
