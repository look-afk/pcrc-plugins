import re
from plugins._base import PluginBase


class ColorConverterPlugin(PluginBase):
    NAME = "color_converter"
    VERSION = "1.0"
    DESCRIPTION = "Преобразует HEX-цвет в RGB и HSL для веб-дизайна."
    AUTHOR = "look-afk"
    COMMANDS = {"color_info": "Информация о цвете: color_info #a78bfa"}

    async def handle(self, cmd: str, param: str) -> str:
        value = param.strip().lstrip("#")
        if not re.fullmatch(r"(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value):
            return "Укажи HEX-цвет в формате #RGB или #RRGGBB."
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
        rf, gf, bf = r / 255, g / 255, b / 255
        maximum, minimum = max(rf, gf, bf), min(rf, gf, bf)
        light = (maximum + minimum) / 2
        hue = saturation = 0.0
        delta = maximum - minimum
        if delta:
            saturation = delta / (1 - abs(2 * light - 1))
            if maximum == rf:
                hue = ((gf - bf) / delta) % 6
            elif maximum == gf:
                hue = (bf - rf) / delta + 2
            else:
                hue = (rf - gf) / delta + 4
            hue *= 60
        return f"HEX: #{value.upper()}\nRGB: {r}, {g}, {b}\nHSL: {round(hue)}°, {round(saturation * 100)}%, {round(light * 100)}%"
