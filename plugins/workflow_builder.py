"""Create, inspect and export reusable PCRC workflows without duplicating core commands."""
import json
import re
from pathlib import Path
from plugins._base import PluginBase

DATA = Path(__file__).resolve().parent / "workflow_builder_data.json"
NAME = "workflow_builder"

def _load():
    try:
        obj = json.loads(DATA.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}

def _save(obj):
    DATA.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

class WorkflowBuilderPlugin(PluginBase):
    NAME = "workflow_builder"
    VERSION = "1.0"
    DESCRIPTION = "Конструктор повторяемых сценариев: хранит шаги и экспортирует план, не исполняя команды скрытно."
    AUTHOR = "look-afk"
    COMMANDS = {
        "wf_help": "Справка Workflow Builder",
        "wf_list": "Список сценариев",
        "wf_new": "Создать сценарий: wf_new <имя> | <описание>",
        "wf_add": "Добавить шаг: wf_add <имя> | <текст шага>",
        "wf_show": "Показать сценарий: wf_show <имя>",
        "wf_remove": "Удалить сценарий: wf_remove <имя>",
        "wf_export": "Экспортировать план сценария: wf_export <имя>",
    }

    async def handle(self, cmd, param):
        data = _load()
        arg = (param or "").strip()
        if cmd == "wf_help":
            return "WORKFLOW BUILDER\nwf_new deploy | Подготовка релиза\nwf_add deploy | Проверить статус\nwf_show deploy\nwf_export deploy\n\nСценарии хранят планы шагов. Плагин не запускает команды автоматически."
        if cmd == "wf_list":
            if not data:
                return "Сценариев пока нет. Используй wf_new <имя> | <описание>."
            return "WORKFLOWS\n" + "\n".join(f"• {k} — {v.get('description','')} ({len(v.get('steps', []))} шаг.)" for k,v in sorted(data.items()))
        if cmd == "wf_new":
            parts = arg.split("|", 1)
            name = parts[0].strip().lower() if parts else ""
            if not re.fullmatch(r"[a-z0-9_-]{2,32}", name):
                return "Имя: 2–32 символа — латиница, цифры, _ или -. Пример: wf_new morning | Утренний чек-лист"
            if name in data:
                return f"Сценарий '{name}' уже существует."
            data[name] = {"description": parts[1].strip()[:180] if len(parts)>1 else "Без описания", "steps": []}
            _save(data)
            return f"✓ Создан сценарий: {name}\nДобавь шаги через wf_add {name} | <текст>."
        if cmd == "wf_add":
            parts = arg.split("|", 1)
            if len(parts) != 2 or not parts[1].strip():
                return "Формат: wf_add <имя> | <текст шага>"
            key, step = parts[0].strip().lower(), parts[1].strip()
            if key not in data:
                return f"Сценарий '{key}' не найден."
            if len(data[key]["steps"]) >= 30:
                return "Лимит — 30 шагов на сценарий."
            data[key]["steps"].append(step[:240])
            _save(data)
            return f"✓ Шаг {len(data[key]['steps'])} добавлен в '{key}'."
        if cmd in ("wf_show", "wf_export", "wf_remove"):
            key = arg.lower()
            if key not in data:
                return "Укажи существующее имя сценария. Список: wf_list"
            if cmd == "wf_remove":
                del data[key]; _save(data)
                return f"Удалён сценарий '{key}'."
            item = data[key]
            lines = [f"WORKFLOW / {key}", item.get("description", ""), ""]
            lines += [f"{i}. {s}" for i,s in enumerate(item.get("steps", []), 1)] or ["Шагов пока нет."]
            if cmd == "wf_export":
                lines += ["", "Экспорт — это план для проверки и ручного запуска; команды не выполняются автоматически."]
            return "\n".join(lines)
        return "Неизвестная команда."
