"""Explicit Windows app blocklist for the PCRC client.

The monitor only runs after appblock_enable and only matches exact executable names
added by the user. It uses psutil directly: no shell, subprocess, registry hooks,
startup persistence, or console windows.
"""
import asyncio
import getpass
import json
import os
import re
from pathlib import Path

import psutil
from plugins._base import PluginBase


_PROTECTED = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "svchost.exe",
    "explorer.exe", "dwm.exe", "fontdrvhost.exe", "python.exe", "pythonw.exe",
}
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,78}\.exe", re.IGNORECASE)


def _config_path() -> Path:
    root = Path(os.environ.get("APPDATA") or Path.home() / ".local" / "share")
    folder = root / "PCRC" / "plugin_data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "app_blocker.json"


def _read_config() -> dict:
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid config")
    except (OSError, ValueError):
        data = {}
    blocked = data.get("blocked", [])
    if not isinstance(blocked, list):
        blocked = []
    clean = sorted({
        name for name in blocked
        if isinstance(name, str) and _NAME_RE.fullmatch(name)
        and name.casefold() not in _PROTECTED
    })
    return {"enabled": data.get("enabled") is True, "blocked": clean}


def _save_config(data: dict) -> None:
    path = _config_path()
    temp = path.with_suffix(".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, path)


class AppBlockerPlugin(PluginBase):
    NAME = "app_blocker"
    VERSION = "1.0"
    DESCRIPTION = (
        "Windows: blocks selected applications by closing matching processes. "
        "Exact .exe names only; no terminal windows, shell commands, registry hooks, "
        "or automatic startup. Enable and disable it explicitly."
    )
    AUTHOR = "look-afk"
    COMMANDS = {
        "ab_help": "Справка App Blocker",
        "ab_add": "Добавить приложение: ab_add notepad.exe",
        "ab_remove": "Убрать приложение: ab_remove notepad.exe",
        "ab_list": "Показать список заблокированных приложений",
        "ab_enable": "Включить блокировку приложений",
        "ab_disable": "Выключить блокировку приложений",
        "ab_status": "Показать состояние App Blocker",
    }

    def __init__(self):
        self._monitor_task = None
        self._running = False

    async def on_load(self) -> None:
        config = _read_config()
        if config["enabled"] and os.name == "nt":
            self._start_monitor()

    async def on_unload(self) -> None:
        self._stop_monitor()

    def _start_monitor(self) -> None:
        if os.name != "nt" or (self._monitor_task and not self._monitor_task.done()):
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor())

    def _stop_monitor(self) -> None:
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        self._monitor_task = None

    async def _monitor(self) -> None:
        current_user = getpass.getuser().casefold()
        try:
            while self._running:
                config = _read_config()
                if not config["enabled"]:
                    break
                blocked = {name.casefold() for name in config["blocked"]}
                if blocked:
                    for proc in psutil.process_iter(["pid", "name", "username"]):
                        try:
                            info = proc.info
                            name = (info.get("name") or "").casefold()
                            if name not in blocked or name in _PROTECTED:
                                continue
                            owner = (info.get("username") or "").rsplit(chr(92), 1)[-1].casefold()
                            if not owner or owner != current_user:
                                continue
                            if proc.pid == os.getpid():
                                continue
                            proc.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                            continue
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            raise
        finally:
            self._running = False
            self._monitor_task = None

    async def handle(self, cmd: str, param: str) -> str:
        arg = (param or "").strip()
        config = _read_config()

        if cmd == "ab_help":
            return (
                "APP BLOCKER (Windows)\n"
                "ab_add notepad.exe  — добавить приложение\n"
                "ab_remove notepad.exe — убрать приложение\n"
                "ab_list — список\n"
                "ab_enable — включить\n"
                "ab_disable — выключить\n"
                "ab_status — состояние\n\n"
                "Указывай точное имя .exe из Диспетчера задач. "
                "Плагин закрывает только совпадающие приложения текущего пользователя. "
                "Он не запускает терминал и не меняет системные настройки."
            )

        if os.name != "nt":
            return "App Blocker поддерживается только на Windows."

        if cmd == "ab_add":
            name = arg if arg.lower().endswith(".exe") else arg + ".exe"
            if not _NAME_RE.fullmatch(name):
                return "Имя должно быть точным именем .exe, например notepad.exe."
            if name.casefold() in _PROTECTED:
                return "Это системный или защищённый процесс; добавление запрещено."
            if name.casefold() not in {x.casefold() for x in config["blocked"]}:
                config["blocked"].append(name)
                config["blocked"].sort(key=str.casefold)
                _save_config(config)
            return f"Добавлено: {name}. Блокировка {'активна' if config['enabled'] else 'пока выключена'}. Включить: ab_enable."

        if cmd == "ab_remove":
            name = arg if arg.lower().endswith(".exe") else arg + ".exe"
            before = len(config["blocked"])
            config["blocked"] = [x for x in config["blocked"] if x.casefold() != name.casefold()]
            if len(config["blocked"]) == before:
                return "Такого приложения в списке нет."
            _save_config(config)
            return f"Удалено из списка: {name}."

        if cmd == "ab_list":
            if not config["blocked"]:
                return "Список пуст. Добавь приложение: ab_add notepad.exe"
            return "APP BLOCKER LIST\n" + "\n".join(
                f"• {name}" for name in config["blocked"]
            )

        if cmd == "ab_enable":
            if not config["blocked"]:
                return "Список пуст. Сначала добавь приложение: ab_add notepad.exe"
            config["enabled"] = True
            _save_config(config)
            self._start_monitor()
            return "App Blocker включён. Будут закрываться только приложения из списка для текущего пользователя."

        if cmd == "ab_disable":
            config["enabled"] = False
            _save_config(config)
            self._stop_monitor()
            return "App Blocker выключен."

        if cmd == "ab_status":
            active = bool(config["enabled"] and self._running)
            return (
                f"App Blocker: {'ВКЛЮЧЁН' if active else 'ВЫКЛЮЧЕН'}\n"
                f"Приложений в списке: {len(config['blocked'])}\n"
                "Платформа: Windows"
            )

        return "Неизвестная команда. Используй ab_help."
