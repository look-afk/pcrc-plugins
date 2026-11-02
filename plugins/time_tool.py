from datetime import datetime, timezone
from plugins._base import PluginBase


class TimeToolPlugin(PluginBase):
    NAME = "time_tool"
    VERSION = "1.0"
    DESCRIPTION = "Показывает UTC-время и преобразует Unix timestamp в дату."
    AUTHOR = "look-afk"
    COMMANDS = {
        "utc_now": "Текущее время устройства в UTC: utc_now",
        "timestamp_date": "Unix timestamp в дату UTC: timestamp_date <секунды>",
    }

    async def handle(self, cmd: str, param: str) -> str:
        if cmd == "utc_now":
            return datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            stamp = float(param.strip())
            if abs(stamp) > 253402300799:
                return "Timestamp вне поддерживаемого диапазона."
            return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")
        except (ValueError, OverflowError, OSError):
            return "Укажи Unix timestamp в секундах, например: timestamp_date 1735689600"
