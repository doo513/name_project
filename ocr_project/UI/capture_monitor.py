import importlib
from typing import Callable, Optional, Tuple

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

try:
    MSS = importlib.import_module("mss")
except Exception:
    MSS = None


Region = Tuple[int, int, int, int]


class CaptureMonitor:
    def __init__(
        self,
        parent: tk.Misc,
        region: Region,
        interval_seconds: float = 2.0,
        source_lang: str = "en",
        target_lang: str = "ko",
        on_frame: Optional[Callable[[Region, object, bool], None]] = None,
        on_save: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        on_translate: Optional[Callable[[], None]] = None,
        on_reselect: Optional[Callable[[Region], None]] = None,
    ) -> None:
        self.parent = parent
        self.region = region
        self.interval_seconds = interval_seconds
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.on_frame = on_frame
        self.on_save = on_save
        self.on_stop = on_stop
        self.on_translate = on_translate
        self.on_reselect = on_reselect

        self.active = False
        self.capture_job = None
        self._stopped = False
        self._reselecting = False
        self.outline_windows = []

        self._build_window()

    def _build_window(self) -> None:
        x1, y1, x2, y2 = self.region
        width = x2 - x1
        height = y2 - y1

        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()

        panel_width = 480
        panel_height = 620
        panel_x = min(max(10, x1), max(10, screen_width - panel_width - 10))

        if y2 + 10 + panel_height <= screen_height:
            panel_y = y2 + 10
        else:
            panel_y = max(10, y1 - panel_height - 10)

        self.win = tk.Toplevel(self.parent)
        self.win.title("OCR 번역 패널")
        self.win.geometry(f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1a1a2e")
        self.win.minsize(480, 560)
        self.win.protocol("WM_DELETE_WINDOW", self.stop)
        self.win.bind("<Configure>", self._on_window_resized)

        header = tk.Frame(self.win, bg="#4B4FA6", height=40)
        header.pack(fill="x")
        tk.Label(
            header,
            text=f"OCR 번역 - {width}x{height}",
            fg="white",
            bg="#4B4FA6",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=8)

        self.status_var = tk.StringVar(value="Ready to capture.")
        self.status_label = tk.Label(
            self.win,
            textvariable=self.status_var,
            fg="#00ff88",
            bg="#1a1a2e",
            font=("Segoe UI", 9),
            wraplength=390,
            justify="left",
        )
        self.status_label.pack(anchor="w", padx=12, pady=(8, 0), fill="x")

        btn_row = tk.Frame(self.win, bg="#1a1a2e")
        btn_row.pack(side="bottom", fill="x", padx=12, pady=(4, 0))

        tk.Label(
            btn_row,
            text="원본:",
            fg="white",
            bg="#1a1a2e",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 4))

        self.source_lang_var = tk.StringVar(value=self.source_lang)
        source_combo = ttk.Combobox(
            btn_row,
            textvariable=self.source_lang_var,
            values=["ko", "en", "ja", "zh", "es", "fr", "de", "ru", "ar"],
            state="readonly",
            width=6,
        )
        source_combo.pack(side="left", padx=(0, 4))

        tk.Label(
            btn_row,
            text="->",
            fg="white",
            bg="#1a1a2e",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=4)

        tk.Label(
            btn_row,
            text="번역:",
            fg="white",
            bg="#1a1a2e",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 4))

        self.translate_target_var = tk.StringVar(value=self.target_lang)
        target_combo = ttk.Combobox(
            btn_row,
            textvariable=self.translate_target_var,
            values=["ko", "en", "ja", "zh", "es", "fr", "de", "ru", "ar"],
            state="readonly",
            width=6,
        )
        target_combo.pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="다시 번역",
            width=10,
            command=self.request_translate,
            bg="#9b59b6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(4, 0))

        btn_row2 = tk.Frame(self.win, bg="#1a1a2e")
        btn_row2.pack(side="bottom", fill="x", padx=12, pady=(4, 12))

        tk.Button(
            btn_row2,
            text="레이어 재설정",
            width=12,
            command=self.request_reselect_area,
            bg="#5E66F2",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Button(
            btn_row2,
            text="저장",
            width=8,
            command=self.request_save,
            bg="#2a9d5b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            btn_row,
            text="중지",
            width=8,
            command=self.stop,
            bg="#ff6b6b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right")

        result_frame = tk.LabelFrame(
            self.win,
            text="확정 OCR / 번역 결과",
            bg="#1a1a2e",
            fg="#00ff88",
            padx=8,
            pady=8,
        )
        result_frame.pack(fill="both", expand=True, padx=12, pady=(10, 4))

        scrollbar = tk.Scrollbar(result_frame)
        scrollbar.pack(side="right", fill="y")

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
            yscrollcommand=scrollbar.set,
        )
        self.result_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.result_text.yview)
        self.result_text.insert("1.0", "Waiting for OCR result...")

    def get_source_lang(self) -> str:
        if hasattr(self, 'source_lang_var'):
            return self.source_lang_var.get()
        return "en"

    def get_translate_target(self) -> str:
        if hasattr(self, 'translate_target_var'):
            return self.translate_target_var.get()
        return "ko"

    def _on_window_resized(self, _event=None) -> None:
        width = max(320, self.win.winfo_width() - 90)
        self.result_text.configure(width=max(40, width // 8))
        self.status_label.configure(wraplength=width)

    def start(self) -> None:
        if ImageGrab is None and MSS is None:
            messagebox.showerror("Error", "No screen capture backend is available.")
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
        if not self.active:
            return

        image = self._grab_screen()
        if image is None:
            self.set_status("Capture failed: Unable to capture screen.")
            return

        if callable(self.on_frame):
            self.on_frame(self.region, image, force)

    def _grab_screen(self):
        x1, y1, x2, y2 = self.region

        if ImageGrab is not None:
            try:
                return ImageGrab.grab(bbox=(x1, y1, x2, y2))
            except Exception:
                pass

        if MSS is not None:
            try:
                with MSS.mss() as sct:
                    monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
                    screenshot = sct.grab(monitor)
                    from PIL import Image

                    return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            except Exception:
                pass

        return None

    def request_reselect_area(self) -> None:
        if not self.active and not self._reselecting:
            self.set_status("Capture is stopped.")
            return

        self.set_status("레이어 재설정을 위해 영역 선택을 다시 엽니다.")
        self._pause_for_reselect()

        try:
            from UI.selector import open_selector_window
        except ImportError as exc:
            self._resume_after_reselect_cancelled()
            messagebox.showerror("Error", f"Failed to load region selector.\n{exc}")
            return

        open_selector_window(
            self.parent,
            on_selected=self._on_region_reselected,
            on_cancel=self._resume_after_reselect_cancelled,
        )

    def _pause_for_reselect(self) -> None:
        self._reselecting = True
        self.active = False
        if self.capture_job:
            self.parent.after_cancel(self.capture_job)
            self.capture_job = None
        self._destroy_region_outline()
        if getattr(self, "win", None) and self.win.winfo_exists():
            self.win.withdraw()

    def _resume_after_reselect_cancelled(self) -> None:
        if self._stopped:
            return
        self._reselecting = False
        if getattr(self, "win", None) and self.win.winfo_exists():
            self.win.deiconify()
            self.win.lift()
        self.start()
        self.set_status("레이어 재설정이 취소되어 기존 영역 캡처를 계속합니다.")

    def _on_region_reselected(self, region: Region) -> None:
        self._reselecting = False
        if callable(self.on_reselect):
            self.on_reselect(region)
            return

        self.stop(notify=False)
        self.region = region
        self._stopped = False
        self._build_window()
        self.start()

    def request_translate(self) -> None:
        if callable(self.on_translate):
            self.on_translate()

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
    source_lang: str = "en",
    target_lang: str = "ko",
    on_frame: Optional[Callable[[Region, object, bool], None]] = None,
    on_save: Optional[Callable[[], None]] = None,
    on_stop: Optional[Callable[[], None]] = None,
    on_translate: Optional[Callable[[], None]] = None,
    on_reselect: Optional[Callable[[Region], None]] = None,
) -> CaptureMonitor:
    monitor = CaptureMonitor(
        parent,
        region=region,
        interval_seconds=interval_seconds,
        source_lang=source_lang,
        target_lang=target_lang,
        on_frame=on_frame,
        on_save=on_save,
        on_stop=on_stop,
        on_translate=on_translate,
        on_reselect=on_reselect,
    )
    return monitor
