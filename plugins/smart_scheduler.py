"""Persistent reminder scheduler. It records reminders; it does not run OS commands."""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from plugins._base import PluginBase

DATA=Path(__file__).resolve().parent/"smart_scheduler_tasks.json"

def _read():
    try:
        d=json.loads(DATA.read_text(encoding="utf-8"))
        return d if isinstance(d,list) else []
    except (OSError,ValueError): return []

def _save(d):
    DATA.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")

class SmartSchedulerPlugin(PluginBase):
    NAME = "smart_scheduler"
    VERSION = "1.0"
    DESCRIPTION = "Список задач с датой/временем и статусом; не запускает системные команды и не гарантирует фоновые уведомления."
    AUTHOR = "look-afk"
    COMMANDS = {
        "sched_help": "Справка Smart Scheduler",
        "sched_add": "Добавить напоминание: sched_add YYYY-MM-DD HH:MM | текст",
        "sched_list": "Показать ближайшие напоминания",
        "sched_done": "Отметить выполненным: sched_done <id>",
        "sched_delete": "Удалить задачу: sched_delete <id>",
    }

    async def handle(self,cmd,param):
        arg=(param or "").strip(); tasks=_read()
        if cmd=="sched_help":
            return "SMART SCHEDULER\nsched_add 2026-12-31 18:30 | Проверить релиз\nsched_list\nsched_done 1\nsched_delete 1\nВремя локальное. Это постоянный список задач, не системный планировщик: плагин не запускает команды и не гарантирует уведомление, если клиент не активен."
        if cmd=="sched_add":
            m=re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*\|\s*(.+)$",arg)
            if not m: return "Формат: sched_add YYYY-MM-DD HH:MM | текст напоминания"
            try: due=datetime.strptime(m.group(1)+" "+m.group(2),"%Y-%m-%d %H:%M")
            except ValueError: return "Некорректная дата/время."
            if due<datetime.now()-timedelta(minutes=1): return "Укажи время в будущем."
            text=m.group(3).strip()
            if len(text)>240: return "Текст ограничен 240 символами."
            if len(tasks)>=300: return "Достигнут лимит 300 задач."
            task={"id":max([int(t.get("id",0)) for t in tasks] or [0])+1,"due":due.isoformat(timespec="minutes"),"text":text,"done":False}
            tasks.append(task); _save(tasks)
            return f"✓ Напоминание #{task['id']} сохранено на {due:%d.%m.%Y %H:%M}\n{ text }"
        if cmd=="sched_list":
            if not tasks: return "Список задач пуст."
            now=datetime.now()
            def key(t):
                try:return datetime.fromisoformat(t["due"])
                except (ValueError,KeyError):return now
            rows=sorted(tasks,key=key)[:30]
            return "SMART SCHEDULER\n"+ "\n".join(f"#{t['id']} {'✓' if t.get('done') else '○'} {t.get('due','?')} — {t.get('text','')}" for t in rows)
        if cmd in ("sched_done","sched_delete"):
            try: ident=int(arg)
            except ValueError: return f"Формат: {cmd} <id>"
            task=next((t for t in tasks if t.get("id")==ident),None)
            if not task: return "Задача с таким ID не найдена."
            if cmd=="sched_done": task["done"]=True; _save(tasks); return f"✓ Задача #{ident} отмечена выполненной."
            tasks=[t for t in tasks if t.get("id")!=ident]; _save(tasks); return f"Задача #{ident} удалена."
        return "Неизвестная команда."
