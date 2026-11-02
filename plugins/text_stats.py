from collections import Counter
from plugins._base import PluginBase


class TextStatsPlugin(PluginBase):
    NAME = "text_stats"
    VERSION = "1.0"
    DESCRIPTION = "Считает символы, слова, строки и частые слова в переданном тексте."
    AUTHOR = "look-afk"
    COMMANDS = {"text_stats": "Статистика текста: text_stats <текст>"}

    async def handle(self, cmd: str, param: str) -> str:
        if not param:
            return "Передай текст после команды."
        words = param.split()
        common = Counter(w.strip('.,!?;:()[]{}\"\'').lower() for w in words)
        common = [(word, count) for word, count in common.most_common(5) if word]
        top = ", ".join(f"{word} ({count})" for word, count in common) or "нет"
        return (
            f"Символов: {len(param)}\n"
            f"Без пробелов: {sum(not ch.isspace() for ch in param)}\n"
            f"Слов: {len(words)}\n"
            f"Строк: {len(param.splitlines()) or 1}\n"
            f"Уникальных слов: {len(set(w.lower() for w in words))}\n"
            f"Частые слова: {top}"
        )
