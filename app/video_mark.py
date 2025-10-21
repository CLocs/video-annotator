import argparse
import csv
import os
import sys
import tkinter as tk
from datetime import datetime

from pathlib import Path
from tkinter import filedialog, messagebox

# CRITICAL: Set up DLL search path BEFORE importing VLC
# This ensures libvlc.dll and libvlccore.dll can be found on Windows
if getattr(sys, 'frozen', False) and sys.platform.startswith('win'):
    # Running as PyInstaller executable on Windows
    exe_dir = os.path.dirname(sys.executable)
    
    # Add executable directory to DLL search path
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetDllDirectoryW(exe_dir)
        print(f"Set DLL directory to: {exe_dir}")
    except Exception as e:
        print(f"Warning: Could not set DLL directory: {e}")
    
    # Also add to PATH as a fallback
    os.environ['PATH'] = exe_dir + os.pathsep + os.environ.get('PATH', '')
    print(f"Added {exe_dir} to PATH")
    
    # Set VLC_PLUGIN_PATH environment variable to help VLC find plugins
    vlc_plugin_path = os.path.join(exe_dir, "vlc")
    if os.path.exists(vlc_plugin_path):
        os.environ['VLC_PLUGIN_PATH'] = vlc_plugin_path
        print(f"Set VLC_PLUGIN_PATH to: {vlc_plugin_path}")

try:
    import vlc  # python-vlc
    
    # If running as frozen executable, try to set the VLC library path explicitly
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        libvlc_path = os.path.join(exe_dir, "libvlc.dll")
        if os.path.exists(libvlc_path):
            # Try to load VLC with explicit path
            try:
                import ctypes
                # Pre-load the VLC DLLs to help resolve dependencies
                ctypes.CDLL(os.path.join(exe_dir, "libvlccore.dll"))
                ctypes.CDLL(libvlc_path)
                print(f"Pre-loaded VLC DLLs from: {exe_dir}")
            except Exception as e:
                print(f"Warning: Could not pre-load VLC DLLs: {e}")
                
except ImportError:
    print("Missing dependency: python-vlc. Install with `pip install python-vlc`.")
    sys.exit(1)


def resource_path(rel_path: str) -> str:
    """Return absolute path to resource, works in dev and in PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)  # set by PyInstaller at runtime
    base_path = Path(base) if base else Path(__file__).parent
    return str(base_path / rel_path)


def get_desktop_path():
    """Get the Desktop path for the current user across platforms."""
    try:
        import os
        
        # Windows-specific Desktop paths
        if sys.platform.startswith('win'):
            desktop_paths = [
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),  # OneDrive Desktop
                os.path.join(os.path.expanduser("~"), "OneDrive - *", "Desktop"),  # Corporate OneDrive
            ]
            
            # Also try environment variables
            if 'USERPROFILE' in os.environ:
                desktop_paths.insert(0, os.path.join(os.environ['USERPROFILE'], "Desktop"))
            
            # Check for OneDrive Desktop in common locations
            onedrive_paths = [
                os.path.join(os.path.expanduser("~"), "OneDrive"),
                os.path.join(os.environ.get('ONEDRIVE', ''), '') if 'ONEDRIVE' in os.environ else None,
            ]
            
            for onedrive in onedrive_paths:
                if onedrive and os.path.exists(onedrive):
                    onedrive_desktop = os.path.join(onedrive, "Desktop")
                    if os.path.exists(onedrive_desktop):
                        return onedrive_desktop
        else:
            # Unix-like systems
            desktop_paths = [
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.path.join(os.path.expanduser("~"), "desktop"),  # Linux sometimes lowercase
            ]
        
        # Check all desktop paths
        for path in desktop_paths:
            if path and os.path.exists(path):
                return path
        
        # Fallback to home directory if Desktop not found
        return os.path.expanduser("~")
    except:
        # Ultimate fallback to current directory
        return "."


def get_default_csv_filename(video_path=None):
    """Generate default CSV filename with current date, video name, and username, saved to Desktop."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Try to get username from various sources
    username = "YOUR_NAME"  # fallback
    try:
        import getpass
        username = getpass.getuser()
    except (ImportError, OSError):
        try:
            username = os.environ.get('USER', os.environ.get('USERNAME', 'YOUR_NAME'))
        except:
            pass
    
    # Get video name (first 12 characters, sanitized)
    video_name = ""
    if video_path and os.path.exists(video_path):
        video_filename = os.path.basename(video_path)
        # Remove extension and get first 12 characters
        video_name = os.path.splitext(video_filename)[0][:12]
        # Sanitize filename (remove invalid characters)
        import re
        video_name = re.sub(r'[<>:"/\\|?*]', '_', video_name)
        if video_name:
            video_name = f"_{video_name}"
    
    # Get Desktop path and create full filename
    desktop = get_desktop_path()
    filename = f"{today}{video_name}_marks_{username}.csv"
    return os.path.join(desktop, filename)


class VideoMarkerApp:
    def __init__(self, master, video_path=None, out_csv="marks.csv", min_gap_ms=250):
        self.master = master
        master.title("Video Timestamp Marker")

        # --- State ---
        self.video_path = video_path
        self.out_csv = out_csv
        self.min_gap_ms = min_gap_ms      # debounce between marks
        self.last_mark_ms = -10_000       # last mark time (video ms)
        self.marks_ms = []                # collected marks in ms
        self.player = None
        self.instance = None
        self.media = None
        self._is_playing = False
        self._total_duration_ms = 0

        # --- UI Layout ---
        self._build_ui()

        # Keyboard bindings
        master.bind("<space>", self.toggle_play_pause)
        master.bind("<Key-m>", self.key_mark)
        master.bind("<Key-M>", self.key_mark)
        master.bind("<Key-u>", self.undo_last)
        master.bind("<Key-U>", self.undo_last)
        master.protocol("WM_DELETE_WINDOW", self.on_close)

        # If a video path is provided, load it
        if self.video_path:
            self.load_video(self.video_path)

    def _build_ui(self):
        # Top bar: open video, play/pause, save
        toolbar = tk.Frame(self.master)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        self.btn_open = tk.Button(toolbar, text="Open Video…", command=self.open_video_dialog)
        self.btn_open.pack(side=tk.LEFT, padx=4)

        self.btn_play = tk.Button(toolbar, text="▶ Play (Space)", command=self.toggle_play_pause, width=12, font=("Arial", 10))
        self.btn_play.pack(side=tk.LEFT, padx=4)

        self.btn_save = tk.Button(toolbar, text="Save CSV", command=self.save_csv)
        self.btn_save.pack(side=tk.LEFT, padx=4)

        self.lbl_out = tk.Label(toolbar, text=f"Output: {self.out_csv}")
        self.lbl_out.pack(side=tk.LEFT, padx=12)

        # Video canvas
        self.video_panel = tk.Frame(self.master, bg="black", width=960, height=540)
        self.video_panel.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.video_panel.update_idletasks()

        # Bottom controls
        controls = tk.Frame(self.master)
        controls.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)

        self.btn_mark = tk.Button(controls, text="MARK (double-click)", height=2, command=self.ignore_single_click)
        self.btn_mark.pack(side=tk.LEFT, padx=6, ipadx=10, ipady=8)
        # Bind true double-click on left mouse
        self.btn_mark.bind("<Double-Button-1>", self.double_click_mark)

        self.btn_undo = tk.Button(controls, text="Undo (U)", command=self.undo_last)
        self.btn_undo.pack(side=tk.LEFT, padx=6)

        self.lbl_status = tk.Label(controls, text="Ready")
        self.lbl_status.pack(side=tk.LEFT, padx=12)

        # Marks listbox
        right = tk.Frame(self.master)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=6)
        
        # Time display above marks
        time_frame = tk.Frame(right)
        time_frame.pack(fill=tk.X, pady=(0, 6))
        self.lbl_time = tk.Label(time_frame, text="00:00:00 / 00:00:00", font=("Courier", 10), fg="blue")
        self.lbl_time.pack(side=tk.LEFT)
        
        tk.Label(right, text="Marks (s)").pack()
        self.listbox = tk.Listbox(right, width=18, height=20)
        self.listbox.pack(fill=tk.Y, expand=False)

    # --- Video ---
    def _ensure_vlc(self):
        if self.instance is None:
            try:
                # Configure VLC for PyInstaller executable
                if getattr(sys, 'frozen', False):
                    # Running as PyInstaller executable
                    # For single-file executables, VLC files should be in the same directory as the .exe
                    # Note: DLL search path is already set up at module import time
                    exe_dir = os.path.dirname(sys.executable)
                    vlc_plugin_dir = os.path.join(exe_dir, "vlc")
                    libvlc_dll = os.path.join(exe_dir, "libvlc.dll")
                    
                    vlc_args = []
                    vlc_found = False
                    
                    # Strategy 1: Check for VLC files in executable directory (for single-file build)
                    if os.path.exists(libvlc_dll) and os.path.exists(vlc_plugin_dir):
                        vlc_args.append(f'--plugin-path={vlc_plugin_dir}')
                        print(f"Using VLC from executable directory: {exe_dir}")
                        print(f"VLC plugins at: {vlc_plugin_dir}")
                        vlc_found = True
                    
                    # Strategy 2: Check for VLC in PyInstaller temp directory (for bundled resources)
                    if not vlc_found:
                        vlc_path = resource_path("vlc")
                        if os.path.exists(vlc_path):
                            vlc_args.append(f'--plugin-path={vlc_path}')
                            print(f"Using bundled VLC plugins at: {vlc_path}")
                            vlc_found = True
                    
                    # Strategy 3: Try system VLC installation
                    if not vlc_found:
                        vlc_paths = [
                            "C:\\Program Files\\VideoLAN\\VLC",
                            "C:\\Program Files (x86)\\VideoLAN\\VLC",
                            "C:\\VLC"
                        ]
                        for vlc_path in vlc_paths:
                            plugins_dir = os.path.join(vlc_path, "plugins")
                            if os.path.exists(vlc_path) and os.path.exists(plugins_dir):
                                vlc_args.append(f'--plugin-path={plugins_dir}')
                                print(f"Using system VLC at: {vlc_path}")
                                vlc_found = True
                                break
                    
                    # Try to create VLC instance with the determined arguments
                    if vlc_args:
                        self.instance = vlc.Instance(vlc_args)
                    else:
                        # Last resort: try without any arguments
                        print("Warning: VLC files not found in expected locations")
                        print(f"Executable directory: {exe_dir}")
                        print(f"Looked for libvlc.dll at: {libvlc_dll}")
                        print(f"Looked for plugins at: {vlc_plugin_dir}")
                        print("Attempting VLC initialization without plugin path")
                        self.instance = vlc.Instance()
                        
                else:
                    # Running as script
                    self.instance = vlc.Instance()
                
                if self.instance is None:
                    raise Exception("Failed to create VLC instance")
                    
            except Exception as e:
                # More detailed error message for debugging
                error_msg = f"Failed to initialize VLC player:\n{e}\n\n"
                if getattr(sys, 'frozen', False):
                    exe_dir = os.path.dirname(sys.executable)
                    vlc_plugin_dir = os.path.join(exe_dir, "vlc")
                    libvlc_dll = os.path.join(exe_dir, "libvlc.dll")
                    
                    error_msg += "Please install VLC Media Player:\n\n"
                    error_msg += "1. Download VLC from: https://www.videolan.org/vlc/\n"
                    error_msg += "2. Install VLC (use default installation location)\n"
                    error_msg += "3. Restart VideoMarker\n\n"
                    error_msg += "Note: VideoMarker requires VLC to play videos.\n"
                    error_msg += "The bundled VLC files cannot load due to missing system dependencies."
                else:
                    error_msg += "Please ensure VLC is installed on your system."
                
                messagebox.showerror("VLC Error", error_msg)
                return False
                
        if self.player is None:
            try:
                self.player = self.instance.media_player_new()
                if self.player is None:
                    raise Exception("Failed to create VLC media player")
                # embed into Tk widget
                self._embed_player()
            except Exception as e:
                messagebox.showerror("VLC Error", f"Failed to create VLC media player:\n{e}")
                return False
        
        return True

    def _embed_player(self):
        self.master.update_idletasks()
        hwnd = self.video_panel.winfo_id()
        if sys.platform.startswith('win'):
            self.player.set_hwnd(hwnd)
        elif sys.platform == "darwin":
            self.player.set_nsobject(hwnd)
        else:
            self.player.set_xwindow(hwnd)

    def load_video(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            return
        
        # Ensure VLC is properly initialized
        if not self._ensure_vlc():
            return
            
        try:
            self.media = self.instance.media_new(path)
            self.player.set_media(self.media)
            self.video_path = path
            self.lbl_status.config(text=f"Loaded: {os.path.basename(path)}")
            
            # Update CSV filename to include video name
            self.out_csv = get_default_csv_filename(path)
            self.lbl_out.config(text=f"Output: {os.path.basename(self.out_csv)}")
            
            # Reset duration and update time display
            self._total_duration_ms = 0
            self.update_time_display()
            # Autoplay
            self.play()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video:\n{e}")
            self.lbl_status.config(text="Failed to load video")

    def open_video_dialog(self):
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[("Video files", "*.*")],
        )
        if path:
            self.load_video(path)

    def play(self):
        if self.player is None:
            return
        self.player.play()
        self._is_playing = True
        self.btn_play.config(text="⏸ Pause (Space)")
        # Start time display updates
        self.update_time_display()

    def pause(self):
        if self.player is None:
            return
        self.player.pause()
        self._is_playing = False
        self.btn_play.config(text="▶ Play (Space)")

    def toggle_play_pause(self, event=None):
        if self.player is None:
            return "break"
        if self._is_playing:
            self.pause()
        else:
            self.play()
        return "break"

    def get_time_ms(self):
        if self.player is None:
            return 0
        t = self.player.get_time()  # milliseconds from start
        # Sometimes VLC returns -1 when not ready; clamp to 0
        return max(0, t if t is not None else 0)
    
    def format_time(self, ms):
        """Convert milliseconds to HH:MM:SS format"""
        if ms < 0:
            return "00:00:00"
        seconds = int(ms // 1000)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def update_time_display(self):
        """Update the time display with current position and total duration"""
        if self.player is None:
            self.lbl_time.config(text="00:00:00 / 00:00:00")
            return
        
        current_ms = self.get_time_ms()
        current_time = self.format_time(current_ms)
        
        # Get total duration if not already set
        if self._total_duration_ms == 0:
            duration = self.player.get_length()
            if duration and duration > 0:
                self._total_duration_ms = duration
        
        total_time = self.format_time(self._total_duration_ms)
        self.lbl_time.config(text=f"{current_time} / {total_time}")
        
        # Schedule next update
        if self._is_playing:
            self.master.after(1000, self.update_time_display)  # Update every second

    # --- Marking ---
    def ignore_single_click(self):
        # The button's single-click is bound to this no-op so only double-click fires a mark.
        pass

    def double_click_mark(self, event=None):
        self._mark_event()

    def key_mark(self, event=None):
        self._mark_event()

    def _mark_event(self):
        t_ms = self.get_time_ms()
        # Debounce to avoid accidental duplicates (e.g., two near-identical events)
        if (t_ms - self.last_mark_ms) < self.min_gap_ms:
            self.lbl_status.config(text="(debounced)")
            return
        self.last_mark_ms = t_ms
        self.marks_ms.append(t_ms)
        t_s = t_ms / 1000.0
        self.listbox.insert(tk.END, f"{t_s:.3f}")
        self.lbl_status.config(text=f"Marked @ {t_s:.3f}s")

    def undo_last(self, event=None):
        if not self.marks_ms:
            return "break"
        self.marks_ms.pop()
        if self.listbox.size() > 0:
            self.listbox.delete(self.listbox.size() - 1)
        self.lbl_status.config(text="Undid last mark")
        return "break"

    # --- Saving ---
    def open_folder(self, folder_path):
        """Open the folder containing the saved file."""
        try:
            import subprocess
            import platform
            
            folder = os.path.dirname(folder_path)
            if not os.path.exists(folder):
                messagebox.showerror("Error", f"Folder does not exist:\n{folder}")
                return
                
            if platform.system() == "Windows":
                # Use shell=True for Windows explorer
                subprocess.run(f'explorer "{folder}"', shell=True, check=False)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder], check=False)
            else:  # Linux and others
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")

    def show_save_dialog(self, file_path, mark_count):
        """Show custom save dialog with Open Folder button."""
        dialog = tk.Toplevel(self.master)
        dialog.title("File Saved")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Success message
        success_label = tk.Label(main_frame, text=f"✓ Successfully saved {mark_count} marks!", 
                               font=("Arial", 12, "bold"), fg="green")
        success_label.pack(pady=(0, 10))
        
        # File path
        path_label = tk.Label(main_frame, text="Saved to:", font=("Arial", 10))
        path_label.pack(anchor="w")
        
        # File path in a frame with scrollbar for long paths
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(5, 15))
        
        path_text = tk.Text(path_frame, height=3, wrap=tk.WORD, font=("Courier", 9))
        path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_text.insert(tk.END, file_path)
        path_text.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(path_frame, orient=tk.VERTICAL, command=path_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        path_text.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        open_folder_btn = tk.Button(button_frame, text="Open Folder", 
                                  command=lambda: self.open_folder(file_path),
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        open_folder_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="Close", 
                            command=dialog.destroy,
                            font=("Arial", 10))
        close_btn.pack(side=tk.RIGHT)

    def save_csv_silent(self):
        """Save CSV without showing dialog (for auto-save)."""
        try:
            # Ensure directory exists
            outdir = os.path.dirname(self.out_csv) or "."
            os.makedirs(outdir, exist_ok=True)
            with open(self.out_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_seconds"])
                for ms in self.marks_ms:
                    writer.writerow([f"{ms/1000.0:.3f}"])
            self.lbl_status.config(text=f"Saved: {self.out_csv}")
            return True
        except Exception as e:
            self.lbl_status.config(text=f"Save failed: {e}")
            return False

    def save_csv(self):
        # Save as one column: timestamp_seconds
        try:
            # Ensure directory exists
            outdir = os.path.dirname(self.out_csv) or "."
            os.makedirs(outdir, exist_ok=True)
            with open(self.out_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_seconds"])
                for ms in self.marks_ms:
                    writer.writerow([f"{ms/1000.0:.3f}"])
            self.lbl_status.config(text=f"Saved: {self.out_csv}")
            self.show_save_dialog(self.out_csv, len(self.marks_ms))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{e}")

    def on_close(self):
        # Auto-save on exit and show dialog if there are marks
        if self.marks_ms:
            try:
                # Save silently first
                if self.save_csv_silent():
                    # Show dialog after successful save, but don't destroy main window yet
                    self.show_save_dialog_on_close()
                    return  # Don't destroy yet, let the dialog handle it
            except Exception as e:
                messagebox.showerror("Error", f"Failed to auto-save on exit:\n{e}")
        
        # If no marks or save failed, proceed with normal close
        self._cleanup_and_close()
    
    def _cleanup_and_close(self):
        """Clean up resources and close the application."""
        if self.player is not None:
            try:
                self.player.stop()
            except Exception:
                pass
        self.master.destroy()
    
    def show_save_dialog_on_close(self):
        """Show save dialog that handles closing the main window."""
        dialog = tk.Toplevel(self.master)
        dialog.title("File Saved")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Success message
        success_label = tk.Label(main_frame, text=f"✓ Successfully saved {len(self.marks_ms)} marks!", 
                               font=("Arial", 12, "bold"), fg="green")
        success_label.pack(pady=(0, 10))
        
        # File path
        path_label = tk.Label(main_frame, text="Saved to:", font=("Arial", 10))
        path_label.pack(anchor="w")
        
        # File path in a frame with scrollbar for long paths
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(5, 15))
        
        path_text = tk.Text(path_frame, height=3, wrap=tk.WORD, font=("Courier", 9))
        path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_text.insert(tk.END, self.out_csv)
        path_text.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(path_frame, orient=tk.VERTICAL, command=path_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        path_text.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        open_folder_btn = tk.Button(button_frame, text="Open Folder", 
                                  command=lambda: self.open_folder(self.out_csv),
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        open_folder_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="Close", 
                            command=lambda: self._close_dialog_and_app(dialog),
                            font=("Arial", 10))
        close_btn.pack(side=tk.RIGHT)
    
    def _close_dialog_and_app(self, dialog):
        """Close the dialog and then close the main application."""
        dialog.destroy()
        self._cleanup_and_close()


def main():
    parser = argparse.ArgumentParser(description="Simple video event marker → CSV")
    parser.add_argument("--video", type=str, default=None, help="Path to video file")
    parser.add_argument("--out", type=str, default=None, help="Output CSV path")
    parser.add_argument("--mingap", type=int, default=250, help="Debounce between marks (ms)")
    args = parser.parse_args()
    
    # Generate default output filename if not provided
    if args.out is None:
        args.out = get_default_csv_filename(args.video)

    root = tk.Tk()
    app = VideoMarkerApp(root, video_path=args.video, out_csv=args.out, min_gap_ms=args.mingap)
    root.geometry("1100x800")
    root.mainloop()


if __name__ == "__main__":
    main()
