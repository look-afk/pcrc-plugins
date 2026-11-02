import secrets
import string
from plugins._base import PluginBase


class PasswordGeneratorPlugin(PluginBase):
    NAME = "password_generator"
    VERSION = "1.0"
    DESCRIPTION = "Создаёт случайные пароли локально с помощью криптографически стойкого генератора."
    AUTHOR = "look-afk"
    COMMANDS = {"password_gen": "Создать пароль: password_gen [длина 12-64]"}

    async def handle(self, cmd: str, param: str) -> str:
        try:
            length = int(param.strip()) if param.strip() else 20
        except ValueError:
            return "Укажи длину от 12 до 64."
        if not 12 <= length <= 64:
            return "Длина должна быть от 12 до 64 символов."
        alphabet = string.ascii_letters + string.digits + "!@#$%&*+-_?"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in password) and any(c.isupper() for c in password)
                    and any(c.isdigit() for c in password) and any(c in "!@#$%&*+-_?" for c in password)):
                return password
