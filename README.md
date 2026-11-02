# pcrc-plugins

Каталог плагинов PCRC. Статический сайт на GitHub Pages, без сервера и базы.

## Как это работает
1. Плагин — файл `plugins/<name>.py` (класс от `PluginBase`, как в `pcrc-client/plugins/_base.py`).
2. При каждом push/PR GitHub Actions запускает `tools/build_index.py`: проверяет файлы (код не выполняется),
   считает sha256 и собирает `site/index.json`.
3. Из ветки `main` сайт автоматически публикуется на Pages.
4. Пользователь копирует с сайта готовую команду `plugin_install <url> <sha256>`.

## Добавить плагин
Fork → положить `plugins/<name>.py` → Pull Request. Проверка в PR покажет ошибки формата.
Требования: имя файла = `NAME`, строка `NAME = "..."` (один пробел вокруг `=`), `DESCRIPTION`, непустой `COMMANDS`,
LF-переводы строк, до 200 КБ. Перед слиянием владелец читает код.

## Запуск проверки локально
    python tools/build_index.py
