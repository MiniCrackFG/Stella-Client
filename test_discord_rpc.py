#!/usr/bin/env python3
"""Test script to debug Discord RPC connection"""

from pypresence import Presence
import time

# Your Client ID
CLIENT_ID = 1503205471379783810

print("=" * 60)
print("DISCORD RPC CONNECTION TEST")
print("=" * 60)
print(f"\nClient ID: {CLIENT_ID}")
print(f"Type: {type(CLIENT_ID).__name__}")

# Check if Discord is running
print("\n1. Checking Discord connection...")
print("   Make sure Discord is:")
print("   ✓ Running")
print("   ✓ Status set to 'Online' (not Invisible)")
print("   ✓ Not in Do Not Disturb mode")

# Try to connect
print("\n2. Attempting to connect...")
try:
    rpc = Presence(CLIENT_ID)
    rpc.connect()
    time.sleep(1)
    print("   ✓ Connection successful!")
    
    # Try to update
    print("\n3. Updating RPC status...")
    rpc.update(
        state="Testing",
        details="RPC is working!",
        large_text="Stella Client"
    )
    print("   ✓ RPC update successful!")
    print("\n✓ Everything works! Check Discord for your activity.")
    
    time.sleep(3)
    rpc.close()
    
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    print(f"\n   Error: {str(e)}")
    
    if "Client ID" in str(e) or "4000" in str(e):
        print("\n   ⚠️  THE PROBLEM IS YOUR CLIENT ID!")
        print("   - Go to: https://discord.com/developers/applications")
        print("   - Create a NEW application or verify your existing one")
        print("   - Copy the 'Application ID' from the General tab")
        print("   - Replace CLIENT_ID with the correct ID")
    elif "Connection" in str(e):
        print("\n   ⚠️  DISCORD CONNECTION ISSUE!")
        print("   - Make sure Discord is running")
        print("   - Try restarting Discord")
        print("   - Check if your Discord status is Online")

print("=" * 60)
