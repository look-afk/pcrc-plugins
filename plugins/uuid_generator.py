import uuid
from plugins._base import PluginBase


class UuidGeneratorPlugin(PluginBase):
    NAME = "uuid_generator"
    VERSION = "1.0"
    DESCRIPTION = "Генерирует случайные UUID для тестовых данных и разработки."
    AUTHOR = "look-afk"
    COMMANDS = {"uuid_gen": "Создать UUID v4: uuid_gen [количество 1-10]"}

    async def handle(self, cmd: str, param: str) -> str:
        try:
            count = int(param.strip()) if param.strip() else 1
        except ValueError:
            return "Укажи количество от 1 до 10."
        if not 1 <= count <= 10:
            return "Количество должно быть от 1 до 10."
        return "\n".join(str(uuid.uuid4()) for _ in range(count))
