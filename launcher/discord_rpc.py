"""
Discord RPC Module for Stella Client
Handles all Discord Rich Presence functionality
"""

import logging
from pypresence import Presence
import time

# Discord Application Configuration
CLIENT_ID = 1503205471379783810

# Global RPC instance
rpc_instance = None


def init_rpc():
    """Initialize Discord RPC connection"""
    global rpc_instance
    try:
        logging.info(f"[Discord RPC] Connecting with Application ID: {CLIENT_ID}")
        rpc_instance = Presence(CLIENT_ID)
        rpc_instance.connect()
        time.sleep(0.5)
        logging.info("✓ [Discord RPC] Connected successfully")
        return rpc_instance
    except Exception as e:
        logging.info(f"✗ [Discord RPC] Connection failed: {e}")
        logging.info("\n⚠️  Troubleshooting:")
        logging.info("   1. Make sure Discord is running")
        logging.info("   2. Verify the Application ID in Discord Developer Portal")
        logging.info("   3. Set your Discord status to 'Online'")
        return None


def update_playing():
    """Update RPC status while playing Minecraft"""
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
            logging.info("✓ [Discord RPC] Status: Playing Minecraft")
        except Exception as e:
            logging.info(f"✗ [Discord RPC] Update failed: {e}")


def update_menu():
    """Update RPC status in main menu"""
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
            logging.info("✓ [Discord RPC] Status: In Main Menu")
        except Exception as e:
            logging.info(f"✗ [Discord RPC] Update failed: {e}")


def close_rpc():
    """Close Discord RPC connection"""
    global rpc_instance
    if rpc_instance:
        try:
            # Primero clear la actividad
            rpc_instance.clear()
            # Esperar 0.5 segundos para que Discord procese
            time.sleep(0.5)
            # Luego cierra la conexión
            rpc_instance.close()
            logging.info("✓ [Discord RPC] Disconnected")
        except Exception as e:
            logging.info(f"✗ [Discord RPC] Disconnect error: {e}")
        finally:
            rpc_instance = None
