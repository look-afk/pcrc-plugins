"""Проверяет плагины и собирает site/index.json. Плагины НЕ выполняются — только разбор через ast."""
import ast, hashlib, json, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "plugins", ROOT / "site"
MAX_SIZE = 200 * 1024

# Что плагин умеет — по импортам. Это подсказка для читателя, а не защита.
# Ключи — полные имена модулей: urllib.parse (кодирование строк) сети не касается, urllib.request — касается.
IMPORT_FLAGS = {
    "subprocess": "запускает программы", "ctypes": "низкоуровневый доступ",
    "winreg": "реестр Windows", "socket": "сеть", "requests": "интернет",
    "urllib.request": "интернет", "urllib3": "интернет", "http.client": "интернет",
    "aiohttp": "интернет", "shutil": "файлы", "pyautogui": "управляет мышью и клавиатурой",
    "pickle": "небезопасная десериализация",
}
CALL_FLAGS = {"eval": "динамический код", "exec": "динамический код", "__import__": "динамический код"}


def load_core() -> set:
    f = Path(__file__).with_name("core_commands.txt")
    if not f.exists():
        print("! tools/core_commands.txt не найден — проверка пересечений со встроенными командами пропущена")
        return set()
    return {l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def import_flags(n) -> set:
    mods = []
    if isinstance(n, ast.Import):
        mods = [a.name for a in n.names]
    elif isinstance(n, ast.ImportFrom):
        base = n.module or ""
        mods = [base] + [f"{base}.{a.name}" for a in n.names]   # from urllib import request
    return {v for m in mods for k, v in IMPORT_FLAGS.items() if m == k or m.startswith(k + ".")}


def parse(path: Path, raw: bytes, core: set):
    errs, text = [], raw.decode("utf-8")
    tree = ast.parse(text)
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and any(
        (isinstance(b, ast.Name) and b.id == "PluginBase") or
        (isinstance(b, ast.Attribute) and b.attr == "PluginBase") for b in n.bases)), None)
    if not cls:
        return None, ["нет класса, унаследованного от PluginBase"]
    attrs = {}
    for n in cls.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            attrs[n.targets[0].id] = lit(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value:
            attrs[n.target.id] = lit(n.value)

    name = attrs.get("NAME")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", name or ""):
        errs.append("NAME: строчные латинские буквы, цифры и _, 2–32 символа")
    elif path.stem != name:
        errs.append(f"имя файла ({path.stem}.py) должно совпадать с NAME ({name})")
    elif f'NAME = "{name}"' not in text and f"NAME = '{name}'" not in text:
        # PluginManager.delete() ищет плагин в файле по этой точной строке
        errs.append(f'пишите строго NAME = "{name}" (один пробел вокруг =), иначе клиент не сможет удалить плагин')
    if not isinstance(attrs.get("DESCRIPTION"), str) or not attrs["DESCRIPTION"].strip():
        errs.append("DESCRIPTION должен быть непустой строкой")
    cmds = attrs.get("COMMANDS")
    if not isinstance(cmds, dict) or not cmds:
        errs.append("COMMANDS должен быть непустым словарём-литералом")
    else:
        for c in cmds:
            if c in core:
                errs.append(f"команда '{c}' совпадает со встроенной командой клиента")

    flags = set()
    for n in ast.walk(tree):
        flags |= import_flags(n)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in CALL_FLAGS:
            flags.add(CALL_FLAGS[n.func.id])
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("system", "popen"):
            flags.add("запускает программы")
    if errs:
        return None, errs
    return {
        "name": name, "version": str(attrs.get("VERSION", "1.0")),
        "description": attrs["DESCRIPTION"].strip(),
        "author": str(attrs.get("AUTHOR") or "—"),
        "commands": {str(k): str(v) for k, v in cmds.items()},
        "voice_triggers": len(attrs.get("VOICE_TRIGGERS") or {}),
        "button": attrs.get("BUTTON_LABEL") if attrs.get("SHOW_BUTTON") else None,
        "capabilities": sorted(flags),
    }, []


def main():
    core = load_core()
    shutil.rmtree(OUT / "plugins", ignore_errors=True)
    (OUT / "plugins").mkdir(parents=True)
    plugins, failed, seen_cmds = [], False, {}
    for path in sorted(SRC.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        raw = path.read_bytes()
        try:
            if len(raw) > MAX_SIZE:
                info, errs = None, [f"файл больше {MAX_SIZE // 1024} КБ"]
            elif b"\r\n" in raw:
                info, errs = None, ["переводы строк CRLF — сохраните файл с LF"]
            else:
                info, errs = parse(path, raw, core)
        except (SyntaxError, UnicodeDecodeError) as e:
            info, errs = None, [f"не удалось разобрать файл: {e}"]
        for c in (info or {}).get("commands", {}):
            if c in seen_cmds:
                errs.append(f"команда '{c}' уже занята плагином '{seen_cmds[c]}'")
        if errs:
            failed = True
            print(f"✗ {path.name}", *[f"    - {e}" for e in errs], sep="\n")
            continue
        for c in info["commands"]:
            seen_cmds[c] = info["name"]
        info.update(file=f"plugins/{path.name}", size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        shutil.copyfile(path, OUT / info["file"])
        plugins.append(info)
        print(f"✓ {path.name}  sha256={info['sha256'][:12]}…")
    (OUT / "index.json").write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "plugins": plugins},
        ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if failed else 0)


main()
