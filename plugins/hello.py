from plugins._base import PluginBase


class HelloPlugin(PluginBase):
    NAME = "hello"
    VERSION = "1.0"
    DESCRIPTION = "Пример плагина: отвечает приветствием"
    AUTHOR = "look-afk"

    COMMANDS = {"hello": "Поздороваться"}
    SHOW_BUTTON = True
    BUTTON_LABEL = "👋 Hello"
    BUTTON_CMD = "hello"

    async def handle(self, cmd: str, param: str) -> str:
        return f"Привет, {param or 'мир'}!"
