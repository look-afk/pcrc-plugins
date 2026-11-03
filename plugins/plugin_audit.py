"""Static preflight review of Python source. This is NOT an execution sandbox."""
import ast
from plugins._base import PluginBase

# Ключи — полные имена модулей: urllib.parse сам по себе сети не касается.
RISK_IMPORTS = {
    "subprocess":"запуск внешних процессов", "socket":"сетевые соединения",
    "ctypes":"низкоуровневый доступ", "winreg":"изменение/чтение реестра",
    "requests":"HTTP-запросы", "urllib.request":"HTTP-запросы", "urllib3":"HTTP-запросы",
    "http.client":"HTTP-запросы", "aiohttp":"HTTP-запросы", "shutil":"операции с файлами",
    "pyautogui":"управление вводом", "pickle":"опасная десериализация",
}
RISK_CALLS = {"eval":"динамическое выполнение", "exec":"динамическое выполнение",
              "compile":"динамическая компиляция", "__import__":"динамический импорт"}


def _hits(mods):
    return [(k, v) for m in mods for k, v in RISK_IMPORTS.items() if m == k or m.startswith(k + ".")]


class PluginAuditPlugin(PluginBase):
    NAME = "plugin_audit"
    VERSION = "1.0"
    DESCRIPTION = "Статический аудит Python-кода плагина: ищет рискованные импорты и вызовы. Код не запускает и не является песочницей."
    AUTHOR = "look-afk"
    COMMANDS = {
        "audit_help": "Справка аудита",
        "audit_scan": "Проверить вставленный Python-код: audit_scan <код>",
        "audit_rules": "Показать правила аудита",
    }

    async def handle(self,cmd,param):
        if cmd=="audit_help":
            return "PLUGIN AUDIT\naudit_scan <Python-код>\naudit_rules\nПередавай короткий код одной строкой или с разделителем ;. Анализ только статический: он не доказывает безопасность и не заменяет изолированную VM/Windows Sandbox."
        if cmd=="audit_rules":
            return "Проверяются импорты/вызовы с высоким риском: subprocess, socket, ctypes, winreg, requests/urllib.request/urllib3/http.client/aiohttp, shutil, pyautogui, pickle, eval/exec/compile/__import__. Найденный маркер — повод для ручного review, не автоматический вердикт."
        if cmd=="audit_scan":
            source=(param or "").strip()
            if not source: return "Формат: audit_scan <Python-код>"
            if len(source)>6000: return "Лимит ввода — 6000 символов."
            try: tree=ast.parse(source)
            except SyntaxError as e: return f"Синтаксическая ошибка в строке {e.lineno}: {e.msg}"
            findings=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for k,v in _hits([a.name for a in node.names]): findings.append(f"строка {node.lineno}: import {k} — {v}")
                elif isinstance(node,ast.ImportFrom):
                    base=node.module or ""
                    for k,v in _hits([base]+[f"{base}.{a.name}" for a in node.names]): findings.append(f"строка {node.lineno}: from {base} import … ({k}) — {v}")
                elif isinstance(node,ast.Call):
                    fn=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
                    if fn in RISK_CALLS: findings.append(f"строка {node.lineno}: {fn} — {RISK_CALLS[fn]}")
                    if isinstance(node.func,ast.Attribute) and fn in ("system","popen"): findings.append(f"строка {node.lineno}: {fn} — запуск команды/процесса")
            findings=list(dict.fromkeys(findings))
            if not findings: return f"✓ Синтаксис корректен; известных маркеров риска не найдено.\nРазмер: {len(source)} символов.\nЭто не гарантия безопасности: анализ статический."
            return "REVIEW REQUIRED\n"+"\n".join("• "+x for x in findings[:30])+f"\n\nНайдено маркеров: {len(findings)}. Код не выполнялся. Нужна ручная проверка."
        return "Неизвестная команда."
