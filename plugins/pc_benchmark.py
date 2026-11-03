"""Bounded, opt-in micro-benchmark; no sustained load or external dependencies."""
import asyncio
import os
import tempfile
import threading
import time
from plugins._base import PluginBase

_lock = threading.Lock()


def _run(duration: int) -> str:
    """Синхронный тест. Вызывается в отдельном потоке, чтобы не блокировать event loop клиента."""
    if not _lock.acquire(blocking=False):
        return "Тест уже выполняется. Подожди пару секунд."
    try:
        started = time.perf_counter()
        deadline = started + duration
        rounds = 0; x = 1
        while time.perf_counter() < deadline:
            for i in range(1000):
                x = (x*1664525+1013904223+i) & 0xFFFFFFFF
            rounds += 1000
        cpu = time.perf_counter() - started
        mem_started = time.perf_counter()
        try:
            blocks = [bytearray(1024*1024) for _ in range(8)]
            for i, b in enumerate(blocks): b[0] = i
            mem = time.perf_counter() - mem_started
            del blocks
        except MemoryError:
            mem = None
        disk = None
        try:
            with tempfile.NamedTemporaryFile(prefix="pcrc-bench-", delete=True) as f:
                payload = b"PCRC benchmark\n"*4096
                t = time.perf_counter(); f.write(payload); f.flush(); os.fsync(f.fileno())
                f.seek(0); f.read(); disk = time.perf_counter() - t
        except OSError:
            pass
        lines = ["PC BENCHMARK / QUICK", f"CPU loop: {rounds:,} iterations in {cpu:.2f}s",
                 f"Memory allocation (8 MiB): {mem*1000:.1f} ms" if mem is not None else "Memory allocation: not enough memory",
                 "Temporary disk write+read+flush: " + (f"{disk*1000:.1f} ms" if disk is not None else "unavailable"),
                 f"Checksum: {x}", "Quick diagnostic only; close heavy apps and repeat for meaningful comparisons."]
        return "\n".join(lines)
    finally:
        _lock.release()


class PcBenchmarkPlugin(PluginBase):
    NAME = "pc_benchmark"
    VERSION = "1.1"
    DESCRIPTION = "Короткий CPU/память/диск micro-benchmark с ограниченной нагрузкой и измерениями."
    AUTHOR = "look-afk"
    COMMANDS = {
        "bench_help": "Справка и ограничения теста",
        "bench_run": "Запустить короткий тест: bench_run [1-3 секунд]",
    }

    async def handle(self, cmd, param):
        if cmd == "bench_help":
            return "PC BENCHMARK\nbench_run 2\nВыполняется короткий CPU-цикл, выделение ограниченного буфера и временный последовательный I/O-тест. Результаты ориентировочные и не сравнимы между разными системами. Нагрузка ограничена 3 секундами."
        if cmd != "bench_run": return "Неизвестная команда."
        try: duration = max(1, min(3, int((param or "2").strip() or "2")))
        except ValueError: return "Укажи длительность от 1 до 3 секунд."
        return await asyncio.to_thread(_run, duration)
