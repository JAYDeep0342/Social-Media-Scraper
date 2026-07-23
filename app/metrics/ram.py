"""Reusable RAM measurement helpers built on psutil."""

from typing import Optional

import psutil


def get_process_ram_mb(process: Optional[psutil.Process] = None) -> float:
    process = process or psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def get_system_ram_percent() -> float:
    return psutil.virtual_memory().percent
