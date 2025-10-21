#!/usr/bin/env python3
"""
Simple test to verify VLC DLL loading
Run this from the dist directory
"""

import sys
import os

print("=== VLC DLL Loading Test ===")
print(f"Python: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print()

# Test 1: Check if DLLs exist
libvlc_path = "libvlc.dll"
libvlccore_path = "libvlccore.dll"
vlc_plugins = "vlc"

print(f"libvlc.dll exists: {os.path.exists(libvlc_path)}")
print(f"libvlccore.dll exists: {os.path.exists(libvlccore_path)}")
print(f"vlc folder exists: {os.path.exists(vlc_plugins)}")
print()

# Test 2: Try to load DLLs with ctypes
try:
    import ctypes
    
    # Try loading with full path
    full_core_path = os.path.abspath("libvlccore.dll")
    full_lib_path = os.path.abspath("libvlc.dll")
    
    print(f"Loading libvlccore.dll from: {full_core_path}")
    core = ctypes.CDLL(full_core_path)
    print("SUCCESS: libvlccore.dll loaded successfully")
    
    print(f"Loading libvlc.dll from: {full_lib_path}")
    lib = ctypes.CDLL(full_lib_path)
    print("SUCCESS: libvlc.dll loaded successfully")
    print()
except Exception as e:
    print(f"FAILED to load DLLs: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    print()

# Test 3: Try to import vlc module
try:
    print("Importing vlc module...")
    import vlc
    print("✓ vlc module imported successfully")
    print()
except Exception as e:
    print(f"✗ Failed to import vlc: {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 4: Try to create VLC instance
try:
    print("Creating VLC instance...")
    os.environ['VLC_PLUGIN_PATH'] = os.path.join(os.getcwd(), "vlc")
    instance = vlc.Instance(['--plugin-path=vlc'])
    if instance:
        print(f"✓ VLC instance created: {instance}")
        
        print("Creating media player...")
        player = instance.media_player_new()
        if player:
            print(f"✓ Media player created: {player}")
        else:
            print("✗ Failed to create media player (returned None)")
    else:
        print("✗ VLC instance is None")
except Exception as e:
    print(f"✗ Failed to create VLC instance: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
input("Press Enter to exit...")
