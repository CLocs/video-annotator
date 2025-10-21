#!/usr/bin/env python3
"""
Test script to debug VLC initialization issues
"""

import sys
import os
from pathlib import Path

def test_vlc_initialization():
    print("=== VLC Initialization Test ===")
    print(f"Python executable: {sys.executable}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    if getattr(sys, 'frozen', False):
        print(f"Executable directory: {os.path.dirname(sys.executable)}")
        
        # Check for VLC DLLs in executable directory
        exe_dir = os.path.dirname(sys.executable)
        libvlc_dll = os.path.join(exe_dir, "libvlc.dll")
        libvlccore_dll = os.path.join(exe_dir, "libvlccore.dll")
        vlc_plugins = os.path.join(exe_dir, "vlc")
        
        print(f"libvlc.dll exists: {os.path.exists(libvlc_dll)}")
        print(f"libvlccore.dll exists: {os.path.exists(libvlccore_dll)}")
        print(f"vlc plugins directory exists: {os.path.exists(vlc_plugins)}")
        
        if os.path.exists(vlc_plugins):
            print(f"VLC plugins contents: {os.listdir(vlc_plugins)}")
    
    try:
        import vlc
        print("VLC module imported successfully")
        
        # Try different initialization strategies
        strategies = [
            ("No arguments", []),
            ("Plugin path from exe dir", [f'--plugin-path={exe_dir}'] if getattr(sys, 'frozen', False) else []),
            ("Plugin path from vlc subdir", [f'--plugin-path={vlc_plugins}'] if getattr(sys, 'frozen', False) and os.path.exists(vlc_plugins) else []),
        ]
        
        for strategy_name, args in strategies:
            print(f"\nTrying: {strategy_name}")
            try:
                instance = vlc.Instance(args)
                if instance:
                    print(f"VLC instance created successfully with {strategy_name}")
                    
                    # Try to create a media player
                    player = instance.media_player_new()
                    if player:
                        print(f"VLC media player created successfully")
                        return True
                    else:
                        print(f"Failed to create VLC media player")
                else:
                    print(f"VLC instance is None")
            except Exception as e:
                print(f"Failed: {e}")
        
        return False
        
    except ImportError as e:
        print(f"Failed to import VLC: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_vlc_initialization()
    if success:
        print("\nVLC initialization test PASSED")
    else:
        print("\nVLC initialization test FAILED")
    
    input("\nPress Enter to exit...")
