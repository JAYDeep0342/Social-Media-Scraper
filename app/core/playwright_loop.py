"""Windows-only bridge that runs Playwright work on a dedicated
ProactorEventLoop thread.

uvicorn always runs its own loop as `asyncio.SelectorEventLoop`, even on
Windows (see uvicorn/loops/asyncio.py). Windows' SelectorEventLoop can't
create subprocesses or connect pipes (`NotImplementedError` from
`BaseEventLoop._make_subprocess_transport`), which Playwright's async API
relies on for its whole connection to the browser driver process, not just
at launch. So under uvicorn on Windows, Playwright coroutines must run on a
separate ProactorEventLoop instead of uvicorn's own loop.
"""

import asyncio
import sys
import threading
from typing import Awaitable, Dict, Optional, TypeVar

T = TypeVar("T")

_loop: Optional[asyncio.AbstractEventLoop] = None
_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _lock:
        if _loop is not None:
            return _loop

        ready = threading.Event()
        holder: Dict[str, asyncio.AbstractEventLoop] = {}

        def _run() -> None:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            holder["loop"] = loop
            ready.set()
            loop.run_forever()

        threading.Thread(target=_run, name="playwright-loop", daemon=True).start()
        ready.wait()
        _loop = holder["loop"]
        return _loop


async def run_playwright(coro: Awaitable[T]) -> T:
    """Awaits `coro` on the dedicated Playwright loop on Windows; runs it
    inline everywhere else, where the caller's own loop already supports
    subprocesses."""
    if sys.platform != "win32":
        return await coro
    future = asyncio.run_coroutine_threadsafe(coro, _ensure_loop())
    return await asyncio.wrap_future(future)
