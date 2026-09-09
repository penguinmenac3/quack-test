"""
Shared session event loop for executing async fixtures and tests.

All async quack-test work runs on a single event loop that lives for the
whole test session. Libraries with loop-bound singletons (e.g. an MCP or
agent client created once at module level) keep working across runs, fixtures
and tests, instead of colliding with a closed loop from a previous
``asyncio.run()`` call. The loop is closed by the pytest plugin at session end
(or at process exit when quack-test is used outside pytest).
"""

import asyncio
import atexit
from typing import Any, Coroutine

_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run_coroutine(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run a coroutine on the shared session event loop."""
    return _get_loop().run_until_complete(coro)


def close_event_loop() -> None:
    """Shut down and close the shared event loop, if it exists."""
    global _loop
    if _loop is not None and not _loop.is_closed():
        _loop.run_until_complete(_loop.shutdown_asyncgens())
        _loop.run_until_complete(_loop.shutdown_default_executor())
        _loop.close()
    _loop = None


atexit.register(close_event_loop)
