import argparse
import csv
import os
import sys
import tkinter as tk
from datetime import datetime

from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import vlc  # python-vlc
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


def get_default_csv_filename():
    """Generate default CSV filename with current date and username, saved to Desktop."""
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
    
    # Get Desktop path and create full filename
    desktop = get_desktop_path()
    filename = f"{today}_marks_{username}.csv"
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

        self.btn_play = tk.Button(toolbar, text="▶ Play", command=self.toggle_play_pause, width=8, font=("Arial", 10))
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
            self.instance = vlc.Instance()
        if self.player is None:
            self.player = self.instance.media_player_new()
            # embed into Tk widget
            self._embed_player()

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
        self._ensure_vlc()
        self.media = self.instance.media_new(path)
        self.player.set_media(self.media)
        self.video_path = path
        self.lbl_status.config(text=f"Loaded: {os.path.basename(path)}")
        # Reset duration and update time display
        self._total_duration_ms = 0
        self.update_time_display()
        # Autoplay
        self.play()

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
        self.btn_play.config(text="⏸ Pause")
        # Start time display updates
        self.update_time_display()

    def pause(self):
        if self.player is None:
            return
        self.player.pause()
        self._is_playing = False
        self.btn_play.config(text="▶ Play")

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
            messagebox.showinfo("Saved", f"Saved {len(self.marks_ms)} marks to:\n{self.out_csv}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{e}")

    def on_close(self):
        # Auto-save on exit (best-effort)
        if self.marks_ms:
            try:
                self.save_csv()
            except Exception:
                pass
        if self.player is not None:
            try:
                self.player.stop()
            except Exception:
                pass
        self.master.destroy()


def main():
    parser = argparse.ArgumentParser(description="Simple video event marker → CSV")
    parser.add_argument("--video", type=str, default=None, help="Path to video file")
    parser.add_argument("--out", type=str, default=get_default_csv_filename(), help="Output CSV path")
    parser.add_argument("--mingap", type=int, default=250, help="Debounce between marks (ms)")
    args = parser.parse_args()

    root = tk.Tk()
    app = VideoMarkerApp(root, video_path=args.video, out_csv=args.out, min_gap_ms=args.mingap)
    root.geometry("1100x800")
    root.mainloop()


if __name__ == "__main__":
    main()
