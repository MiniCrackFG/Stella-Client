"""
Discord RPC Module for Stella Client
Handles all Discord Rich Presence functionality
"""

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
        print(f"[Discord RPC] Connecting with Application ID: {CLIENT_ID}")
        rpc_instance = Presence(CLIENT_ID)
        rpc_instance.connect()
        time.sleep(0.5)
        print("✓ [Discord RPC] Connected successfully")
        return rpc_instance
    except Exception as e:
        print(f"✗ [Discord RPC] Connection failed: {e}")
        print("\n⚠️  Troubleshooting:")
        print("   1. Make sure Discord is running")
        print("   2. Verify the Application ID in Discord Developer Portal")
        print("   3. Set your Discord status to 'Online'")
        return None


def update_playing():
    """Update RPC status while playing Minecraft"""
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.update(
                state="Stella Client",
                details="Playing Minecraft",
                large_text="Stella Client",
                start=time.time()
            )
            print("✓ [Discord RPC] Status: Playing Minecraft")
        except Exception as e:
            print(f"✗ [Discord RPC] Update failed: {e}")


def update_menu():
    """Update RPC status in main menu"""
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.update(
                state="Stella Client",
                details="In Main Menu",
                large_text="Stella Client",
                start=time.time()
            )
            print("✓ [Discord RPC] Status: In Main Menu")
        except Exception as e:
            print(f"✗ [Discord RPC] Update failed: {e}")


def close_rpc():
    """Close Discord RPC connection"""
    global rpc_instance
    if rpc_instance:
        try:
            rpc_instance.close()
            print("✓ [Discord RPC] Disconnected")
        except Exception as e:
            print(f"✗ [Discord RPC] Disconnect error: {e}")
        finally:
            rpc_instance = None
