from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")

_LOOP_LOCK = threading.Lock()
_TASK_LOOP: asyncio.AbstractEventLoop | None = None


def run_async(coro: Awaitable[T]) -> T:
    """Run async task bodies on a stable loop inside Celery worker process."""
    global _TASK_LOOP
    with _LOOP_LOCK:
        if _TASK_LOOP is None or _TASK_LOOP.is_closed():
            _TASK_LOOP = asyncio.new_event_loop()
    return _TASK_LOOP.run_until_complete(coro)
