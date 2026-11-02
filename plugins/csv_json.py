import csv
import io
import json
from plugins._base import PluginBase


class CsvJsonPlugin(PluginBase):
    NAME = "csv_json"
    VERSION = "1.0"
    DESCRIPTION = "Преобразует CSV с заголовками в JSON-массив объектов."
    AUTHOR = "look-afk"
    COMMANDS = {"csv_to_json": "CSV в JSON; первая строка должна содержать заголовки."}

    async def handle(self, cmd: str, param: str) -> str:
        if not param.strip():
            return "Передай CSV с заголовками. Разделитель — запятая; строки разделяй переносами."
        if len(param) > 12000:
            return "Слишком большой ввод: максимум 12 000 символов."
        try:
            reader = csv.DictReader(io.StringIO(param))
            if not reader.fieldnames or any(not name for name in reader.fieldnames):
                return "Первая строка должна содержать непустые названия столбцов."
            rows = list(reader)
            if len(rows) > 200:
                return "Слишком много строк: максимум 200."
            return json.dumps(rows, ensure_ascii=False, indent=2)
        except csv.Error as exc:
            return f"Не удалось разобрать CSV: {exc}"
