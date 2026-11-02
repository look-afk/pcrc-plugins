from plugins._base import PluginBase


class MarkdownTablePlugin(PluginBase):
    NAME = "markdown_table"
    VERSION = "1.0"
    DESCRIPTION = "Создаёт Markdown-таблицу из строк, разделённых вертикальной чертой."
    AUTHOR = "look-afk"
    COMMANDS = {"md_table": "Таблица из строк: md_table Заголовок 1 | Заголовок 2; Значение 1 | Значение 2"}

    async def handle(self, cmd: str, param: str) -> str:
        rows = [line.strip() for line in param.split(";") if line.strip()]
        if not rows:
            return "Формат: md_table Имя | Версия; Alpha | 1.0; Beta | 2.0"
        parsed = [[cell.strip().replace("|", "\\|") for cell in row.split("|")] for row in rows]
        width = len(parsed[0])
        if width < 2:
            return "В каждой строке используй минимум два столбца, разделяя их символом |."
        if any(len(row) != width for row in parsed):
            return "Во всех строках должно быть одинаковое число столбцов."
        header = "| " + " | ".join(parsed[0]) + " |"
        divider = "| " + " | ".join("---" for _ in range(width)) + " |"
        body = ["| " + " | ".join(row) + " |" for row in parsed[1:]]
        return "\n".join([header, divider, *body])
