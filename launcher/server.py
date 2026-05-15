import asyncio
import json
import logging
import threading
import websockets

logger = logging.getLogger(__name__)

_PORT = 17523
_clients = set()
_loop = None


async def _handler(websocket):
    _clients.add(websocket)
    logger.info("Mod connected (%d total)", len(_clients))
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")
                if msg_type == "pong":
                    pass
                elif msg_type == "game_start":
                    logger.info("Game started")
                elif msg_type == "game_stop":
                    logger.info("Game stopped")
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    finally:
        _clients.discard(websocket)
        logger.info("Mod disconnected (%d remaining)", len(_clients))


async def _start():
    async with websockets.serve(_handler, "127.0.0.1", _PORT):
        logger.info("WS server listening on ws://127.0.0.1:%d", _PORT)
        await asyncio.Future()


def start():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(_start())


def stop():
    if _loop and _loop.is_running():
        for ws in set(_clients):
            asyncio.run_coroutine_threadsafe(ws.close(), _loop)
        _loop.call_soon_threadsafe(_loop.stop)


async def _broadcast(data):
    if not _clients:
        return
    msg = json.dumps(data)
    await asyncio.gather(*(c.send(msg) for c in _clients.copy()), return_exceptions=True)


def broadcast(data):
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(data), _loop)
