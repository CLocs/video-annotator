import sys, csv, os, time
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLabel, QListWidget, QMessageBox, QMainWindow
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class VideoMarkerQt(QMainWindow):
    def __init__(self, video_path=None, out_csv=None, min_gap_ms=250):
        super().__init__()
        self.setWindowTitle("Video Timestamp Marker (Qt)")
        self.min_gap_ms = min_gap_ms
        self.last_mark_ms = -10_000
        self.marks_ms = []
        self.out_csv = out_csv or os.path.join(os.path.expanduser("~"), "Desktop", "marks.csv")

        # --- Player ---
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        # --- UI ---
        open_btn = QPushButton("Open Video…")
        open_btn.clicked.connect(self.open_video)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)

        save_btn = QPushButton("Save CSV")
        save_btn.clicked.connect(self.save_csv)

        self.mark_btn = QPushButton("MARK (double-click)")
        self.mark_btn.setMinimumHeight(48)
        self.mark_btn.clicked.connect(lambda: None)  # ignore single click
        self.mark_btn.mouseDoubleClickEvent = self.double_click_mark

        undo_btn = QPushButton("Undo (U)")
        undo_btn.clicked.connect(self.undo_last)

        self.status_lbl = QLabel(f"Output: {self.out_csv}")
        self.listbox = QListWidget()

        top = QHBoxLayout()
        top.addWidget(open_btn)
        top.addWidget(self.play_btn)
        top.addWidget(save_btn)
        top.addStretch(1)

        bottom = QHBoxLayout()
        bottom.addWidget(self.mark_btn)
        bottom.addWidget(undo_btn)
        bottom.addWidget(self.status_lbl, stretch=1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Marks (s)"))
        right.addWidget(self.listbox)

        main = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addLayout(top)
        left_col.addWidget(self.video_widget, stretch=1)
        left_col.addLayout(bottom)
        main.addLayout(left_col, stretch=3)
        main.addLayout(right, stretch=1)

        wrapper = QWidget()
        wrapper.setLayout(main)
        self.setCentralWidget(wrapper)
        self.resize(1100, 700)

        # Shortcuts
        self.addAction(self._mk_action("Space", self.toggle_play))
        self.addAction(self._mk_action("M", self._mark_event))
        self.addAction(self._mk_action("U", self.undo_last))

        if video_path:
            self.load_video(video_path)

    def _mk_action(self, keyseq, slot):
        act = QAction(self)
        act.setShortcut(keyseq)
        act.triggered.connect(slot)
        return act

    # --- Video control ---
    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select video", "", "Video Files (*.*)")
        if path:
            self.load_video(path)

    def load_video(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.play_btn.setText("Pause")
        self.status_lbl.setText(f"Loaded: {os.path.basename(path)}")

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("Play")
        else:
            self.player.play()
            self.play_btn.setText("Pause")

    def current_time_ms(self):
        return max(0, self.player.position())  # ms

    # --- Marking ---
    def double_click_mark(self, event):
        self._mark_event()

    def _mark_event(self):
        t_ms = self.current_time_ms()
        if (t_ms - self.last_mark_ms) < self.min_gap_ms:
            self.status_lbl.setText("(debounced)")
            return
        self.last_mark_ms = t_ms
        self.marks_ms.append(t_ms)
        t_s = t_ms / 1000.0
        self.listbox.addItem(f"{t_s:.3f}")
        self.status_lbl.setText(f"Marked @ {t_s:.3f}s")

    def undo_last(self):
        if not self.marks_ms:
            return
        self.marks_ms.pop()
        if self.listbox.count() > 0:
            self.listbox.takeItem(self.listbox.count() - 1)
        self.status_lbl.setText("Undid last mark")

    # --- Save ---
    def save_csv(self):
        try:
            os.makedirs(os.path.dirname(self.out_csv), exist_ok=True)
            with open(self.out_csv, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp_seconds"])
                for ms in self.marks_ms:
                    w.writerow([f"{ms/1000.0:.3f}"])
            QMessageBox.information(self, "Saved", f"Saved {len(self.marks_ms)} marks to:\n{self.out_csv}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{e}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=str, default=None)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--mingap", type=int, default=250)
    args = ap.parse_args()

    app = QApplication(sys.argv)
    win = VideoMarkerQt(video_path=args.video, out_csv=args.out, min_gap_ms=args.mingap)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
