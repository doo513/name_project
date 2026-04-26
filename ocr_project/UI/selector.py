from typing import Optional, Tuple

import tkinter as tk
from tkinter import messagebox


Region = Tuple[int, int, int, int]


class RegionSelectorWindow:
    def __init__(self, parent: tk.Misc, on_selected=None) -> None:
        self.parent = parent
        self.on_selected = on_selected
        self.selected_region: Optional[Region] = None
        self.rect_id = None
        self.start_x = 0
        self.start_y = 0

        self._build_overlay()

    def _build_overlay(self) -> None:
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()

        self.selection_win = tk.Toplevel(self.parent)
        self.selection_win.attributes("-topmost", True)
        self.selection_win.attributes("-alpha", 0.85)
        self.selection_win.overrideredirect(True)
        self.selection_win.configure(bg="#1a1a2e")
        self.selection_win.geometry(f"{screen_width}x{screen_height}+0+0")
        self.selection_win.focus_force()
        self.selection_win.bind("<Escape>", lambda _event: self.close())

        self.selection_canvas = tk.Canvas(
            self.selection_win,
            bg="#1a1a2e",
            cursor="crosshair",
            highlightthickness=0,
        )
        self.selection_canvas.pack(fill="both", expand=True)

        self.selection_canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.selection_canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.selection_canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        self.hud = tk.Frame(self.selection_win, bg="#0d0d1a", padx=20, pady=15, relief="raised", bd=2)
        self.hud.place(x=20, y=20)

        self.info_var = tk.StringVar(value="Drag to select an OCR area.")
        tk.Label(
            self.hud,
            textvariable=self.info_var,
            fg="#00ff88",
            bg="#0d0d1a",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        tk.Label(
            self.hud,
            text="Drag to select area. Press Esc to cancel.",
            fg="#aaaaaa",
            bg="#0d0d1a",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        btn_frame = tk.Frame(self.hud, bg="#0d0d1a")
        btn_frame.pack(anchor="w", pady=(12, 0))

        tk.Button(
            btn_frame,
            text="Use Area",
            width=10,
            command=self.confirm_selection,
            bg="#00d4aa",
            fg="black",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Button(
            btn_frame,
            text="Cancel",
            width=10,
            command=self.close,
            bg="#444444",
            fg="white",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(8, 0))

    def _on_mouse_down(self, event) -> None:
        self.start_x = event.x
        self.start_y = event.y

        if self.rect_id:
            self.selection_canvas.delete(self.rect_id)

        self.rect_id = self.selection_canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="#2ed3ff",
            width=3,
            dash=(4, 3),
        )

    def _on_mouse_drag(self, event) -> None:
        if not self.rect_id:
            return

        self.selection_canvas.coords(
            self.rect_id,
            self.start_x,
            self.start_y,
            event.x,
            event.y,
        )

    def _on_mouse_up(self, event) -> None:
        if not self.rect_id:
            return

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        self.selected_region = (x1, y1, x2, y2)
        width = x2 - x1
        height = y2 - y1
        self.info_var.set(f"Selected area: {width}x{height} | Click Use Area")

    def confirm_selection(self) -> None:
        if not self.selected_region:
            messagebox.showwarning("Notice", "Please select an area first.")
            return

        x1, y1, x2, y2 = self.selected_region
        if x2 - x1 < 20 or y2 - y1 < 20:
            messagebox.showwarning("Notice", "Area too small.")
            return

        region = self.selected_region
        self.close()

        if callable(self.on_selected):
            self.on_selected(region)

    def close(self) -> None:
        if getattr(self, "selection_win", None) and self.selection_win.winfo_exists():
            self.selection_win.destroy()


def open_selector_window(parent: tk.Misc, on_selected=None) -> RegionSelectorWindow:
    return RegionSelectorWindow(parent, on_selected=on_selected)
