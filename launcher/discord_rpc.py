import logging
from pypresence import Presence
import time

logger = logging.getLogger(__name__)

CLIENT_ID = 1503205471379783810
rpc_instance = None


def init_rpc():
    global rpc_instance
    try:
        logger.info("[Discord RPC] Connecting...")
        rpc_instance = Presence(CLIENT_ID)
        rpc_instance.connect()
        logger.info("[Discord RPC] Connected")
        return rpc_instance
    except Exception as e:
        logger.info(f"[Discord RPC] Connection failed: {e}")
        return None


def update_playing():
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.update(
                name="Stella Client",
                state="Stella Client",
                details="Playing Minecraft",
                large_image="stella_client",
                large_text="Stella Client",
                start=time.time()
            )
            logger.info("[Discord RPC] Status: Playing")
        except Exception as e:
            logger.info(f"[Discord RPC] Update failed: {e}")


def update_menu():
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.update(
                name="Stella Client",
                state="Stella Client",
                details="In Main Menu",
                large_image="stella_client",
                large_text="Stella Client",
                start=time.time()
            )
            logger.info("[Discord RPC] Status: Menu")
        except Exception as e:
            logger.info(f"[Discord RPC] Update failed: {e}")


def close_rpc():
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.clear()
            rpc_instance.close()
            logger.info("[Discord RPC] Disconnected")
        except Exception as e:
            logger.info(f"[Discord RPC] Disconnect error: {e}")
        finally:
            rpc_instance = None
