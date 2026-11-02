"""Static preflight review of Python source. This is NOT an execution sandbox."""
import ast
from plugins._base import PluginBase

RISK_IMPORTS = {
    "subprocess":"запуск внешних процессов", "socket":"сетевые соединения",
    "ctypes":"низкоуровневый доступ", "winreg":"изменение/чтение реестра",
    "requests":"HTTP-запросы", "urllib":"HTTP/URL-доступ", "shutil":"операции с файлами",
    "pyautogui":"управление вводом", "pickle":"опасная десериализация",
}
RISK_CALLS = {"eval":"динамическое выполнение", "exec":"динамическое выполнение",
              "compile":"динамическая компиляция", "__import__":"динамический импорт"}

class PluginSandboxPlugin(PluginBase):
    NAME = "plugin_sandbox"
    VERSION = "1.0"
    DESCRIPTION = "Статический preflight-аудит Python-кода плагина; не запускает переданный код и не является изоляцией."
    AUTHOR = "look-afk"
    COMMANDS = {
        "sandbox_help": "Справка аудита",
        "sandbox_scan": "Проверить вставленный Python-код: sandbox_scan <код>",
        "sandbox_rules": "Показать правила аудита",
    }

    async def handle(self,cmd,param):
        if cmd=="sandbox_help":
            return "PLUGIN PREFLIGHT\nsandbox_scan <Python-код>\nsandbox_rules\nПередавай короткий код одной строкой или с разделителем ;. Анализ только статический. Он не доказывает безопасность и не заменяет изолированную VM/Windows Sandbox."
        if cmd=="sandbox_rules":
            return "Проверяются импорты/вызовы с высоким риском: subprocess, socket, ctypes, winreg, requests/urllib, shutil, pyautogui, pickle, eval/exec/compile/__import__. Найденный маркер — повод для ручного review, не автоматический вердикт."
        if cmd=="sandbox_scan":
            source=(param or "").strip()
            if not source: return "Формат: sandbox_scan <Python-код>"
            if len(source)>6000: return "Лимит ввода — 6000 символов."
            try: tree=ast.parse(source)
            except SyntaxError as e: return f"Синтаксическая ошибка в строке {e.lineno}: {e.msg}"
            findings=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        root=alias.name.split(".")[0]
                        if root in RISK_IMPORTS: findings.append(f"строка {node.lineno}: import {root} — {RISK_IMPORTS[root]}")
                elif isinstance(node,ast.ImportFrom):
                    root=(node.module or "").split(".")[0]
                    if root in RISK_IMPORTS: findings.append(f"строка {node.lineno}: from {root} — {RISK_IMPORTS[root]}")
                elif isinstance(node,ast.Call):
                    fn=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
                    if fn in RISK_CALLS: findings.append(f"строка {node.lineno}: {fn} — {RISK_CALLS[fn]}")
                    if isinstance(node.func,ast.Attribute) and fn in ("system","popen"): findings.append(f"строка {node.lineno}: {fn} — запуск команды/процесса")
            findings=list(dict.fromkeys(findings))
            if not findings: return f"✓ Синтаксис корректен; известных маркеров риска не найдено.\nРазмер: {len(source)} символов.\nЭто не гарантия безопасности: анализ статический."
            return "REVIEW REQUIRED\n"+"\n".join("• "+x for x in findings[:30])+f"\n\nНайдено маркеров: {len(findings)}. Код не выполнялся. Нужна ручная проверка."
        return "Неизвестная команда."
