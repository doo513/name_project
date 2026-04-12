import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import tkinter as tk
from tkinter import messagebox
import threading

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

try:
    import numpy as np
except Exception:
    np = None

try:
    from CORE.ocr_engine import get_ocr_engine
except ImportError:
    get_ocr_engine = None


class SelectorWindow:
    def __init__(self, parent: tk.Misc, on_selected=None) -> None:
        self.parent = parent
        self.on_selected = on_selected
        self.ocr_engine = get_ocr_engine() if get_ocr_engine else None
        self.capture_interval = 2.0
        self.monitoring = False
        self.capture_job = None
        self.captured_texts = []
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        
        self._create_selection_overlay()

    def _create_selection_overlay(self) -> None:
        self.selection_win = tk.Toplevel(self.parent)
        self.selection_win.attributes("-topmost", True)
        self.selection_win.attributes("-alpha", 0.3)
        self.selection_win.overrideredirect(True)
        sw = self.selection_win.winfo_screenwidth()
        sh = self.selection_win.winfo_screenheight()
        self.selection_win.geometry(f"{sw}x{sh}+0+0")
        
        self.selection_canvas = tk.Canvas(self.selection_win, bg="black", cursor="crosshair", highlightthickness=0)
        self.selection_canvas.pack(fill="both", expand=True)
        
        self.selection_canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.selection_canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.selection_canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        
        self.hud = tk.Frame(self.selection_win, bg="#111111", padx=10, pady=8)
        self.hud.place(x=20, y=20)
        
        self.info_var = tk.StringVar(value="Drag to select area | Start to capture")
        tk.Label(self.hud, textvariable=self.info_var, fg="white", bg="#111111", font=("Arial", 10, "bold")).pack()
        
        btn_frame = tk.Frame(self.hud, bg="#111111")
        btn_frame.pack(pady=(8, 0))
        tk.Button(btn_frame, text="Start", width=8, command=self._start_capture, bg="#2ed3ff", font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(btn_frame, text="Cancel", width=8, command=self._close, bg="#666666", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=(5, 0))
        
        self.rect_id = None
        self.start_x = 0
        self.start_y = 0

    def _on_mouse_down(self, event) -> None:
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.selection_canvas.delete(self.rect_id)
        self.rect_id = self.selection_canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#2ed3ff", width=3, dash=(4, 3)
        )

    def _on_mouse_drag(self, event) -> None:
        if not self.rect_id:
            return
        self.selection_canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_mouse_up(self, event) -> None:
        if not self.rect_id:
            return
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        self.selected_region = (x1, y1, x2, y2)
        w, h = x2 - x1, y2 - y1
        self.info_var.set(f"Selected: {w}x{h} | Press Start")

    def _start_capture(self) -> None:
        if not self.selected_region:
            messagebox.showwarning("Notice", "Please select an area first.")
            return
        
        x1, y1, x2, y2 = self.selected_region
        if x2 - x1 < 20 or y2 - y1 < 20:
            messagebox.showwarning("Notice", "Area too small.")
            return
        
        self.monitoring = True
        self.captured_texts = []
        self.selection_win.attributes("-alpha", 0)
        
        self._create_capture_ui(x1, y1, x2 - x1, y2 - y1)
        self._create_region_border(x1, y1, x2, y2)
        self._capture_loop()

    def _create_capture_ui(self, x: int, y: int, w: int, h: int) -> None:
        self.capture_win = tk.Toplevel(self.parent)
        self.capture_win.attributes("-topmost", True)
        self.capture_win.attributes("-alpha", 0.9)
        self.capture_win.geometry(f"280x180+{x}+{y + h + 10}")
        self.capture_win.configure(bg="#222222")
        
        tk.Label(self.capture_win, text=f"Capturing: {w}x{h}", fg="#2ed3ff", bg="#222222", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        
        self.capture_preview = tk.Label(self.capture_win, text="Starting...", fg="#00ff00", bg="#222222", font=("Consolas", 9), anchor="w", justify="left", wraplen=260)
        self.capture_preview.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_frame = tk.Frame(self.capture_win, bg="#222222")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Stop", width=8, command=self._stop_capture, bg="#ff6b6b", fg="white", font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(btn_frame, text="Reset", width=8, command=self._reset, bg="#888888", fg="white", font=("Arial", 9, "bold")).pack(side="left", padx=(5, 0))

    def _create_region_border(self, x1: int, y1: int, x2: int, y2: int) -> None:
        sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        
        self.border_win = tk.Toplevel(self.parent)
        self.border_win.attributes("-topmost", True)
        self.border_win.attributes("-alpha", 0.01)
        self.border_win.overrideredirect(True)
        self.border_win.geometry(f"{sw}x{sh}+0+0")
        self.border_win.configure(bg="black")
        
        canvas = tk.Canvas(self.border_win, bg="", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(x1, y1, x2, y2, outline="#2ed3ff", width=3)
        canvas.create_text((x1 + x2) // 2, y1 - 15, text="OCR Active", fill="#2ed3ff", font=("Arial", 12, "bold"))

    def _capture_loop(self) -> None:
        if not self.monitoring:
            return
        
        self._do_capture()
        self.capture_job = self.parent.after(int(self.capture_interval * 1000), self._capture_loop)

    def _do_capture(self) -> None:
        if not self.selected_region or not ImageGrab:
            return
        
        try:
            x1, y1, x2, y2 = self.selected_region
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            self._process_image(img)
        except Exception as e:
            print(f"[ERROR] Capture: {e}")

    def _process_image(self, img) -> None:
        def worker():
            try:
                img_array = np.array(img)
                result = self.ocr_engine.read_text_simple(img_array)
                
                if result:
                    new = [t for t in result if t.strip() and t not in self.captured_texts]
                    self.captured_texts.extend(new)
                    self.parent.after(0, lambda r=result: self._update_ui(r))
            except Exception as e:
                print(f"[ERROR] OCR: {e}")
        
        threading.Thread(target=worker, daemon=True).start()

    def _update_ui(self, result: List[str]) -> None:
        if not self.capture_preview:
            return
        
        if result:
            text = '\n'.join(result[:6])
            self.capture_preview.config(text=text, fg="#00ff00")
        else:
            self.capture_preview.config(text="...", fg="#888888")

    def _stop_capture(self) -> None:
        self.monitoring = False
        if self.capture_job:
            self.parent.after_cancel(self.capture_job)
        
        if hasattr(self, 'border_win') and self.border_win:
            self.border_win.destroy()
        
        if hasattr(self, 'capture_win') and self.capture_win:
            self.capture_win.destroy()
        
        self.selection_win.attributes("-alpha", 0.3)
        
        if self.captured_texts and callable(self.on_selected):
            self.on_selected(self.selected_region, None, self.captured_texts)

    def _reset(self) -> None:
        self._stop_capture()
        self.selected_region = None
        self.captured_texts = []
        self.info_var.set("Drag to select area | Start to capture")
        if self.rect_id:
            self.selection_canvas.delete(self.rect_id)
            self.rect_id = None

    def _close(self) -> None:
        self._stop_capture()
        if hasattr(self, 'border_win') and self.border_win:
            try:
                self.border_win.destroy()
            except:
                pass
        self.selection_win.destroy()


def open_selector_window(parent: tk.Misc, on_selected=None) -> SelectorWindow:
    return SelectorWindow(parent, on_selected=on_selected)
