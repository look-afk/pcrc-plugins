import hashlib
from plugins._base import PluginBase


class HashToolPlugin(PluginBase):
    NAME = "hash_tool"
    VERSION = "1.0"
    DESCRIPTION = "Вычисляет SHA-256 для текста без отправки его во внешние сервисы."
    AUTHOR = "look-afk"
    COMMANDS = {"sha256_text": "SHA-256 текста: sha256_text <текст>"}

    async def handle(self, cmd: str, param: str) -> str:
        if not param:
            return "Передай текст после команды."
        digest = hashlib.sha256(param.encode("utf-8")).hexdigest()
        return f"SHA-256: {digest}"
