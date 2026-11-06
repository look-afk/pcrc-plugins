"""Explicit Windows app blocklist for the PCRC client.

The monitor only runs after appblock_enable and only matches exact executable names
added by the user. It uses psutil directly: no shell, subprocess, registry hooks,
startup persistence, or console windows.
"""
import asyncio
import hashlib
import hmac
import secrets
import threading
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
    VERSION = "1.1"
    DESCRIPTION = (
        "Windows app blocklist plus an optional local fullscreen password screen. "
        "The password can be set by an authorized administrator; the overlay has an emergency exit and does "
        "not disable Windows recovery or system controls."
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
        "ab_set_password": "Удалённо задать пароль System Guard (администратор)",
        "ab_system": "Открыть полноэкранную блокировку PCRC",
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
        _GUARD_CLOSE.set()

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
                "ab_add notepad.exe — добавить приложение\n"
                "ab_remove notepad.exe — убрать приложение\n"
                "ab_list — список\n"
                "ab_enable / ab_disable — включить / выключить список\n"
                "ab_status — состояние\n\n"
                "SYSTEM GUARD\n"
                "ab_set_password — открыть локальное окно настройки пароля\n"
                "ab_system — открыть полноэкранное окно с паролем\n"
                "Аварийный выход: Ctrl+Shift+F12.\n"
                "Пароль передаётся администратором через Telegram и хранится на ПК только в виде PBKDF2-хеша."
            )

        if os.name != "nt":
            return "App Blocker и System Guard поддерживаются только на Windows."

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
            return "APP BLOCKER LIST\n" + "\n".join(f"• {name}" for name in config["blocked"])

        if cmd == "ab_enable":
            if not config["blocked"]:
                return "Список пуст. Сначала добавь приложение: ab_add notepad.exe"
            config["enabled"] = True
            _save_config(config)
            self._start_monitor()
            return "App Blocker включён."

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
                f"System Guard: {'ОТКРЫТ' if _GUARD_THREAD and _GUARD_THREAD.is_alive() else 'ЗАКРЫТ'}\n"
                f"Пароль задан: {'ДА' if config.get('guard_hash') and config.get('guard_salt') else 'НЕТ'}"
            )

        if cmd == "ab_set_password":
            if len(arg) < 8:
                return "Укажи пароль длиной минимум 8 символов: ab_set_password <пароль>"
            if len(arg) > 256:
                return "Пароль слишком длинный (максимум 256 символов)."
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", arg.encode("utf-8"), salt, 310_000).hex()
            config["guard_salt"] = salt.hex()
            config["guard_hash"] = digest
            _save_config(config)
            return "Пароль System Guard установлен. Сохранён только PBKDF2-хеш; окно настройки не открывалось."

        if cmd == "ab_system":
            if not (config.get("guard_hash") and config.get("guard_salt")):
                return "Сначала задай пароль локально: ab_set_password"
            if _launch_guard(setup=False):
                return "System Guard открыт на компьютере. Аварийный выход: Ctrl+Shift+F12."
            return "System Guard уже открыт."

        return "Неизвестная команда. Используй ab_help."


_GUARD_CLOSE = threading.Event()
_GUARD_LOCK = threading.Lock()
_GUARD_THREAD = None


def _password_matches(password: str, config: dict) -> bool:
    salt_hex = config.get("guard_salt")
    expected = config.get("guard_hash")
    if not isinstance(salt_hex, str) or not isinstance(expected, str):
        return False
    try:
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 310_000
        ).hex()
    except (ValueError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)


def _launch_guard(setup: bool = False) -> bool:
    global _GUARD_THREAD
    with _GUARD_LOCK:
        if _GUARD_THREAD and _GUARD_THREAD.is_alive():
            return False
        _GUARD_CLOSE.clear()
        _GUARD_THREAD = threading.Thread(
            target=_guard_window, args=(setup,), name="PCRC-SystemGuard", daemon=True
        )
        _GUARD_THREAD.start()
        return True


def _guard_window(setup: bool) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        return

    root = None
    try:
        root = tk.Tk()
        root.title("PCRC System Guard")
        root.configure(bg="#09090f")
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", lambda: None)

        panel = tk.Frame(root, bg="#151522", padx=42, pady=34)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            panel, text="PCRC SYSTEM GUARD", fg="#c4b5fd",
            bg="#151522", font=("Segoe UI", 22, "bold")
        )
        title.pack(pady=(0, 10))

        hint = tk.Label(
            panel, text="Доступ к рабочему экрану временно ограничен",
            fg="#d4d4dc", bg="#151522", font=("Segoe UI", 11)
        )
        hint.pack(pady=(0, 22))

        entry = tk.Entry(
            panel, show="•", width=30, font=("Segoe UI", 16),
            justify="center", relief="flat"
        )
        entry.pack(ipady=9, pady=(0, 12))
        status = tk.Label(panel, text="", fg="#fca5a5", bg="#151522", font=("Segoe UI", 10))
        status.pack(pady=(0, 10))

        def exit_guard():
            _GUARD_CLOSE.set()

        def verify(_event=None):
            cfg = _read_config()
            if _password_matches(entry.get(), cfg):
                _GUARD_CLOSE.set()
            else:
                entry.delete(0, "end")
                status.config(text="Неверный пароль")
                entry.focus_set()

        def emergency(_event=None):
            if messagebox.askyesno(
                "Аварийный выход",
                "Закрыть окно PCRC System Guard? Это не изменит пароль и настройки Windows.",
                parent=root,
            ):
                exit_guard()

        if setup:
            title.config(text="НАСТРОЙКА SYSTEM GUARD")
            hint.config(text="Пароль задаётся локально и хранится в виде PBKDF2-хеша")
            confirm = tk.Entry(
                panel, show="•", width=30, font=("Segoe UI", 16),
                justify="center", relief="flat"
            )
            confirm.pack(ipady=9, pady=(0, 12))
            confirm.insert(0, "")
            confirm_hint = tk.Label(
                panel, text="Повтори пароль", fg="#a1a1aa",
                bg="#151522", font=("Segoe UI", 10)
            )
            confirm_hint.pack()
            confirm.pack_forget()
            confirm_hint.pack_forget()

            def show_setup():
                entry.pack(ipady=9, pady=(0, 12))
                confirm_hint.pack()
                confirm.pack(ipady=9, pady=(0, 12))
                status.pack(pady=(0, 10))
                button.config(text="Сохранить пароль", command=save_password)
                hint.config(text="Минимум 8 символов. Вводи пароль только на этом ПК.")

            def save_password():
                first, second = entry.get(), confirm.get()
                if len(first) < 8:
                    status.config(text="Минимальная длина — 8 символов")
                    return
                if first != second:
                    status.config(text="Пароли не совпадают")
                    return
                salt = secrets.token_bytes(16)
                digest = hashlib.pbkdf2_hmac("sha256", first.encode("utf-8"), salt, 310_000).hex()
                cfg = _read_config()
                cfg["guard_salt"] = salt.hex()
                cfg["guard_hash"] = digest
                _save_config(cfg)
                messagebox.showinfo("PCRC", "Пароль сохранён локально.", parent=root)
                _GUARD_CLOSE.set()

        else:
            button = None
            entry.bind("<Return>", verify)
            entry.focus_set()

        if not setup:
            button = tk.Button(
                panel, text="Разблокировать", command=verify,
                bg="#8b5cf6", fg="white", activebackground="#7c3aed",
                relief="flat", padx=22, pady=10, font=("Segoe UI", 11, "bold")
            )
            button.pack(pady=(0, 12))
        else:
            button = tk.Button(
                panel, text="Сохранить пароль", command=save_password,
                bg="#8b5cf6", fg="white", activebackground="#7c3aed",
                relief="flat", padx=22, pady=10, font=("Segoe UI", 11, "bold")
            )
            button.pack(pady=(0, 12))
            if setup:
                show_setup()

        foot = tk.Label(
            panel, text="Аварийный выход: Ctrl + Shift + F12",
            fg="#a1a1aa", bg="#151522", font=("Segoe UI", 9)
        )
        foot.pack()

        root.bind_all("<Control-Shift-F12>", emergency)
        root.bind_all("<Escape>", lambda _e: "break")

        def poll_close():
            if _GUARD_CLOSE.is_set():
                root.destroy()
                return
            root.after(150, poll_close)

        root.after(150, poll_close)
        root.mainloop()
    except Exception:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
