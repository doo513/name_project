from typing import Callable, Optional, Tuple

import tkinter as tk
from tkinter import messagebox

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None


Region = Tuple[int, int, int, int]


class CaptureMonitor:
    def __init__(
        self,
        parent: tk.Misc,
        region: Region,
        interval_seconds: float = 2.0,
        on_frame: Optional[Callable[[Region, object, bool], None]] = None,
        on_save: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
    ) -> None:
        self.parent = parent
        self.region = region
        self.interval_seconds = interval_seconds
        self.on_frame = on_frame
        self.on_save = on_save
        self.on_stop = on_stop

        self.active = False
        self.capture_job = None
        self._stopped = False
        self.outline_windows = []

        self._build_window()

    def _build_window(self) -> None:
        x1, y1, x2, y2 = self.region
        width = x2 - x1
        height = y2 - y1

        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()

        panel_width = 420
        panel_height = 340
        panel_x = min(max(10, x1), max(10, screen_width - panel_width - 10))

        if y2 + 10 + panel_height <= screen_height:
            panel_y = y2 + 10
        else:
            panel_y = max(10, y1 - panel_height - 10)

        self.win = tk.Toplevel(self.parent)
        self.win.title("Capture OCR Panel")
        self.win.geometry(f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#222222")
        self.win.protocol("WM_DELETE_WINDOW", self.stop)

        tk.Label(
            self.win,
            text=f"Monitoring: {width}x{height}",
            fg="#2ed3ff",
            bg="#222222",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        self.status_var = tk.StringVar(value="Ready to capture.")
        tk.Label(
            self.win,
            textvariable=self.status_var,
            fg="#d7d7d7",
            bg="#222222",
            font=("Segoe UI", 9),
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=12)

        result_frame = tk.LabelFrame(
            self.win,
            text="OCR Output",
            bg="#222222",
            fg="#f0f0f0",
            padx=8,
            pady=8,
        )
        result_frame.pack(fill="both", expand=True, padx=12, pady=(10, 8))

        self.result_text = tk.Text(
            result_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#111111",
            fg="#00ff88",
            insertbackground="#ffffff",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.result_text.pack(fill="both", expand=True)
        self.result_text.insert("1.0", "Waiting for OCR result...")

        btn_row = tk.Frame(self.win, bg="#222222")
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            btn_row,
            text="Recognize Now",
            width=14,
            command=self.request_capture_now,
            bg="#2d6cdf",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Button(
            btn_row,
            text="Save",
            width=10,
            command=self.request_save,
            bg="#2a9d5b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            btn_row,
            text="Stop",
            width=10,
            command=self.stop,
            bg="#ff6b6b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

    def start(self) -> None:
        if ImageGrab is None:
            messagebox.showerror("Error", "Pillow ImageGrab is not available.")
            self.stop()
            return

        self.active = True
        self._show_region_outline()
        self.set_status(f"Capturing every {self.interval_seconds:.1f} seconds.")
        self._capture_loop()

    def focus_panel(self) -> None:
        if getattr(self, "win", None) and self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()

    def _capture_loop(self) -> None:
        if not self.active:
            return

        self._capture_once(force=False)
        self.capture_job = self.parent.after(int(self.interval_seconds * 1000), self._capture_loop)

    def _capture_once(self, force: bool) -> None:
        if not self.active or ImageGrab is None:
            return

        try:
            image = ImageGrab.grab(bbox=self.region)
        except Exception as exc:
            self.set_status(f"Capture failed: {exc}")
            return

        if callable(self.on_frame):
            self.on_frame(self.region, image, force)

    def request_capture_now(self) -> None:
        if not self.active:
            self.set_status("Capture is stopped.")
            return

        self.set_status("Manual recognition requested.")
        self._capture_once(force=True)

    def request_save(self) -> None:
        if callable(self.on_save):
            self.on_save()

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def set_result_text(self, text: str) -> None:
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text or "No text detected.")

    def _show_region_outline(self) -> None:
        self._destroy_region_outline()

        x1, y1, x2, y2 = self.region
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        border = 3
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()

        outer_x = max(0, x1 - border)
        outer_y = max(0, y1 - border)
        outer_width = min(screen_width - outer_x, width + border * 2)
        outer_height = min(screen_height - outer_y, height + border * 2)

        segments = [
            (outer_x, outer_y, outer_width, border),
            (outer_x, min(screen_height - border, y2), outer_width, border),
            (outer_x, outer_y, border, outer_height),
            (min(screen_width - border, x2), outer_y, border, outer_height),
        ]

        for x, y, segment_width, segment_height in segments:
            outline = tk.Toplevel(self.parent)
            outline.overrideredirect(True)
            outline.attributes("-topmost", True)
            outline.attributes("-alpha", 0.85)
            outline.configure(bg="#2ed3ff")
            outline.geometry(f"{segment_width}x{segment_height}+{x}+{y}")
            self.outline_windows.append(outline)

    def _destroy_region_outline(self) -> None:
        for outline in self.outline_windows:
            if outline.winfo_exists():
                outline.destroy()
        self.outline_windows = []

    def stop(self, notify: bool = True) -> None:
        if self._stopped:
            return

        self._stopped = True
        self.active = False

        if self.capture_job:
            self.parent.after_cancel(self.capture_job)
            self.capture_job = None

        self._destroy_region_outline()

        if getattr(self, "win", None) and self.win.winfo_exists():
            self.win.destroy()

        if notify and callable(self.on_stop):
            self.on_stop()


def open_capture_monitor(
    parent: tk.Misc,
    region: Region,
    interval_seconds: float = 2.0,
    on_frame: Optional[Callable[[Region, object, bool], None]] = None,
    on_save: Optional[Callable[[], None]] = None,
    on_stop: Optional[Callable[[], None]] = None,
) -> CaptureMonitor:
    return CaptureMonitor(
        parent,
        region=region,
        interval_seconds=interval_seconds,
        on_frame=on_frame,
        on_save=on_save,
        on_stop=on_stop,
    )
