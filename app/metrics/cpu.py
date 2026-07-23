"""Reusable CPU measurement helpers built on psutil."""

from typing import Optional

import psutil


def get_process_cpu_percent(process: Optional[psutil.Process] = None) -> float:
    """Non-blocking CPU% for the given process (or the current one).

    Note: psutil's cpu_percent must be primed with a first call before a
    later call returns a meaningful delta — callers doing before/after
    measurements should call this once at the start to prime it.
    """
    process = process or psutil.Process()
    return process.cpu_percent(interval=None)


def get_system_cpu_percent() -> float:
    return psutil.cpu_percent(interval=None)
