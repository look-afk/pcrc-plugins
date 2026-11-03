"""Generate a safe starter template for PCRC PluginBase plugins."""
import re
from plugins._base import PluginBase

class PluginDeveloperKit(PluginBase):
    NAME = "plugin_developer_kit"
    VERSION = "1.1"
    DESCRIPTION = "Генератор стартового шаблона и чек-лист публикации PCRC-плагина."
    AUTHOR = "look-afk"
    COMMANDS = {
        "pdk_help": "Справка Plugin Developer Kit",
        "pdk_template": "Создать шаблон: pdk_template <name>",
        "pdk_checklist": "Чек-лист готовности плагина",
    }

    async def handle(self,cmd,param):
        if cmd=="pdk_help":
            return "PLUGIN DEVELOPER KIT\npdk_template my_plugin\npdk_checklist\nИмя: 2–32 символа, латиница/цифры/_. Шаблон выводится в ответ; сохрани его в plugins/<name>.py и проверь локально."
        if cmd=="pdk_checklist":
            return "PUBLISH CHECKLIST\n□ NAME совпадает с именем файла\n□ NAME записан строго как NAME = \"имя\" (иначе клиент не сможет удалить плагин)\n□ COMMANDS уникальны во всём каталоге и не совпадают со встроенными командами клиента\n□ Данные хранятся в %APPDATA%\\PCRC\\plugin_data, а не рядом с файлом плагина\n□ Долгая или блокирующая работа вынесена в asyncio.to_thread\n□ Все параметры валидируются\n□ Ошибки обработаны, вывод ограничен\n□ Нет секретов и токенов\n□ Нет скрытого сбора данных\n□ Не запускает команды/скрипты без явного подтверждения\n□ python tools/build_index.py проходит без ошибок\n□ Код вручную проверен перед PR"
        if cmd=="pdk_template":
            name=(param or "").strip().lower()
            if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}",name): return "Имя: 2–32 символа, начинается с буквы. Пример: pdk_template my_plugin"
            cls="".join(part.title() for part in name.split("_"))+"Plugin"
            return f'''СОХРАНИ КАК plugins/{name}.py\n\nfrom plugins._base import PluginBase\n\n\nclass {cls}(PluginBase):\n    NAME = "{name}"\n    VERSION = "1.0"\n    DESCRIPTION = "Краткое описание плагина"\n    AUTHOR = "your-name"\n\n    COMMANDS = {{\n        "{name}_help": "Показать справку",\n    }}\n\n    async def handle(self, cmd: str, param: str) -> str:\n        if cmd == "{name}_help":\n            return "Добавь сюда описание команд и примеры."\n        return "Неизвестная команда."\n\nПроверь: python tools/build_index.py'''
        return "Неизвестная команда."
