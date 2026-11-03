"""Design and validate command presets; never executes stored commands."""
import json
import os
import re
from pathlib import Path
from plugins._base import PluginBase


def _data() -> Path:
    # Данные лежат вне папки плагинов: она может быть недоступна для записи, а delete не должен их терять.
    root = Path(os.environ.get("APPDATA") or Path.home() / ".local" / "share") / "PCRC" / "plugin_data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "command_studio_presets.json"


def _read():
    try:
        d=json.loads(_data().read_text(encoding="utf-8"))
        return d if isinstance(d,dict) else {}
    except (OSError,ValueError): return {}


def _save(d):
    p = _data(); tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp, p)   # атомарно: обрыв посреди записи не портит файл


class CommandStudioPlugin(PluginBase):
    NAME = "command_studio"
    VERSION = "1.1"
    DESCRIPTION = "Редактор именованных пресетов команд с проверкой формата и экспортом для ручного запуска."
    AUTHOR = "look-afk"
    COMMANDS = {
        "cs_help": "Справка Command Studio",
        "cs_new": "Создать пресет: cs_new <имя> | <описание>",
        "cs_step": "Добавить строку: cs_step <имя> | <команда>",
        "cs_show": "Показать пресет: cs_show <имя>",
        "cs_list": "Список пресетов",
        "cs_delete": "Удалить пресет: cs_delete <имя>",
    }

    async def handle(self,cmd,param):
        arg=(param or "").strip(); d=_read()
        if cmd=="cs_help":
            return "COMMAND STUDIO\ncs_new morning | Проверка перед работой\ncs_step morning | status\ncs_show morning\ncs_list\n\nПлагин хранит строки команд, но не исполняет их. Перед запуском проверь каждую строку и права доступа."
        if cmd=="cs_list":
            return "COMMAND PRESETS\n"+("\n".join(f"• {k} — {v.get('description','')} ({len(v.get('steps',[]))} команд)" for k,v in sorted(d.items())) if d else "Пока пусто.")
        if cmd=="cs_new":
            p=arg.split("|",1); key=p[0].strip().lower()
            if not re.fullmatch(r"[a-z0-9_-]{2,32}",key): return "Имя должно содержать 2–32 символа: латиница, цифры, _ или -."
            if key in d: return "Такой пресет уже существует."
            d[key]={"description":p[1].strip()[:160] if len(p)>1 else "Без описания","steps":[]}; _save(d)
            return f"✓ Пресет '{key}' создан."
        if cmd=="cs_step":
            p=arg.split("|",1)
            if len(p)!=2 or not p[1].strip(): return "Формат: cs_step <имя> | <команда>"
            key,step=p[0].strip().lower(),p[1].strip()
            if key not in d: return "Пресет не найден."
            if len(d[key]["steps"])>=25: return "Лимит — 25 строк."
            if any(c in step for c in "\r\n\x00"): return "Одна команда на строку."
            d[key]["steps"].append(step[:200]); _save(d)
            return f"✓ Строка {len(d[key]['steps'])} добавлена."
        if cmd in ("cs_show","cs_delete"):
            key=arg.lower()
            if key not in d: return "Пресет не найден."
            if cmd=="cs_delete":
                del d[key]; _save(d); return f"Пресет '{key}' удалён."
            p=d[key]
            return f"COMMAND STUDIO / {key}\n{p.get('description','')}\n\n"+("\n".join(f"{i}. {s}" for i,s in enumerate(p.get('steps',[]),1)) if p.get("steps") else "Строк пока нет.")+"\n\nКоманды не исполняются этим плагином."
        return "Неизвестная команда."
