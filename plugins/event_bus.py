"""Small local event journal for plugins; no remote telemetry."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from plugins._base import PluginBase

MAX_EVENTS = 200


def _data() -> Path:
    # Данные лежат вне папки плагинов: она может быть недоступна для записи, а delete не должен их терять.
    root = Path(os.environ.get("APPDATA") or Path.home() / ".local" / "share") / "PCRC" / "plugin_data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "event_bus_events.json"


def _read():
    try:
        obj = json.loads(_data().read_text(encoding="utf-8"))
        return obj if isinstance(obj, list) else []
    except (OSError, ValueError):
        return []


def _write(events):
    p = _data(); tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(events[-MAX_EVENTS:], ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)   # атомарно: обрыв посреди записи не портит файл


class EventBusPlugin(PluginBase):
    NAME = "event_bus"
    VERSION = "1.1"
    DESCRIPTION = "Локальный журнал событий: ручная запись, просмотр и сводка по типам. Автоматической подписки между плагинами нет."
    AUTHOR = "look-afk"
    COMMANDS = {
        "event_help": "Справка Event Bus",
        "event_publish": "Записать событие: event_publish <тип> | <сообщение>",
        "event_recent": "Последние события: event_recent [количество]",
        "event_clear": "Очистить журнал событий",
        "event_stats": "Сводка по типам событий",
    }

    async def handle(self, cmd, param):
        arg = (param or "").strip()
        events = _read()
        if cmd == "event_help":
            return "EVENT BUS\nevent_publish task.completed | Задача завершена\nevent_recent 10\nevent_stats\nevent_clear\nЖурнал локальный, максимум 200 записей. Это ручной event journal; автоматическая подписка других плагинов требует поддержки в клиентском API."
        if cmd == "event_publish":
            parts = arg.split("|", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                return "Формат: event_publish <тип> | <сообщение>"
            kind = parts[0].strip()[:48]
            message = parts[1].strip()[:500]
            events.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "type": kind, "message": message})
            _write(events)
            return f"✓ Событие записано\nТип: {kind}\nВсего в журнале: {min(len(events), MAX_EVENTS)}"
        if cmd == "event_recent":
            try: count = max(1, min(30, int(arg or "10")))
            except ValueError: return "Количество должно быть числом от 1 до 30."
            if not events: return "Журнал пока пуст."
            return "RECENT EVENTS\n" + "\n".join(f"{e.get('at','?')} · [{e.get('type','?')}] {e.get('message','')}" for e in events[-count:][::-1])
        if cmd == "event_clear":
            _write([])
            return "Журнал событий очищен."
        if cmd == "event_stats":
            counts = {}
            for e in events: counts[e.get("type", "unknown")] = counts.get(e.get("type", "unknown"), 0) + 1
            if not counts: return "Событий пока нет."
            return "EVENT STATS\n" + "\n".join(f"• {k}: {v}" for k,v in sorted(counts.items(), key=lambda x: (-x[1], x[0])))
        return "Неизвестная команда."
