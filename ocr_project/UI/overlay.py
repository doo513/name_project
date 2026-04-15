import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Dict, Optional


class OverlayWindow:
    def __init__(
        self,
        parent: tk.Misc,
        initial_text: str = "",
        selected_region=None,
        capture_path: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        on_saved=None,
    ) -> None:
        self.parent = parent
        self.on_saved = on_saved

        self.selected_region = selected_region
        self.capture_path = capture_path

        if data:
            if "selected_region" in data:
                self.selected_region = data.get("selected_region")
            if "capture_path" in data:
                self.capture_path = data.get("capture_path")
            if "initial_text" in data and not initial_text:
                initial_text = str(data.get("initial_text") or "")

        self.win = tk.Toplevel(parent)
        self.win.title("Overlay Info")
        self.win.geometry("480x320+30+30")
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.9)
        self.win.configure(bg="#111111")

        self._build_ui()
        self._render_meta()
        self.set_result_text(initial_text or self._default_text())

    def is_open(self) -> bool:
        return bool(getattr(self, "win", None) and self.win.winfo_exists())

    def _build_ui(self) -> None:
        header = tk.Frame(self.win, padx=10, pady=8, bg="#111111")
        header.pack(fill="x")

        tk.Label(
            header,
            text="Non-intrusive Overlay",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg="#111111",
        ).pack(side="left")

        info = tk.Frame(self.win, bg="#111111")
        info.pack(fill="x", padx=10)

        self.region_var = tk.StringVar(value="Region: None")
        self.capture_var = tk.StringVar(value="Capture: None")

        tk.Label(info, textvariable=self.region_var, fg="#d5d5d5", bg="#111111", anchor="w").pack(fill="x")
        tk.Label(info, textvariable=self.capture_var, fg="#d5d5d5", bg="#111111", anchor="w").pack(fill="x", pady=(2, 8))

        self.text = tk.Text(
            self.win,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
            height=9,
            bg="#1a1a1a",
            fg="#f0f0f0",
            insertbackground="#ffffff",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        footer = tk.Frame(self.win, padx=10, pady=10, bg="#111111")
        footer.pack(fill="x")

        tk.Button(footer, text="Copy", width=10, command=self.copy_result).pack(side="left")
        tk.Button(footer, text="Save", width=10, command=self.save_result).pack(side="right")
        tk.Button(footer, text="Close", width=10, command=self.win.destroy).pack(side="right", padx=(0, 6))

    def _render_meta(self) -> None:
        self.region_var.set(f"Region: {self.selected_region if self.selected_region else 'None'}")
        self.capture_var.set(f"Capture: {self.capture_path if self.capture_path else 'None'}")

    def update_context(self, selected_region=None, capture_path: Optional[str] = None) -> None:
        self.selected_region = selected_region
        self.capture_path = capture_path
        self._render_meta()

    def _default_text(self) -> str:
        return (
            "Overlay note\n"
            "- transparent top-most window\n"
            "- lightweight information delivery\n"
        )

    def set_result_text(self, text: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)

    def get_result_text(self) -> str:
        return self.text.get("1.0", "end").strip()

    def copy_result(self) -> None:
        content = self.get_result_text()
        if not content:
            messagebox.showwarning("Notice", "No content to copy.")
            return
        self.win.clipboard_clear()
        self.win.clipboard_append(content)
        messagebox.showinfo("Done", "Copied overlay text.")

    def save_result(self) -> None:
        content = self.get_result_text()
        if not content:
            messagebox.showwarning("Notice", "No content to save.")
            return

        saved = self._try_save_with_db(content)
        if saved:
            messagebox.showinfo("Done", "Saved to database.")
            if callable(self.on_saved):
                self.on_saved(content)
            return

        saved = self._save_to_txt_file(content)
        if saved and callable(self.on_saved):
            self.on_saved(content)

    def _try_save_with_db(self, content: str) -> bool:
        try:
            from CORE import db
        except Exception:
            return False

        region_str = str(self.selected_region) if self.selected_region else None

        save_ocr = getattr(db, "save_ocr_result", None)
        if callable(save_ocr):
            try:
                save_ocr(content=content, source_region=region_str)
                return True
            except Exception:
                pass

        for name in ("save_study_item", "insert_ocr_result"):
            fn = getattr(db, name, None)
            if callable(fn):
                try:
                    fn(content)
                    return True
                except Exception:
                    pass

        return False

    def _save_to_txt_file(self, content: str) -> bool:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_name = f"overlay_{timestamp}.txt"

        file_path = filedialog.asksaveasfilename(
            parent=self.win,
            title="Save Overlay Text",
            defaultextension=".txt",
            initialfile=initial_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not file_path:
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Done", f"Saved file:\n{os.path.basename(file_path)}")
            return True
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save file.\n{exc}")
            return False


def open_overlay_window(
    parent: tk.Misc,
    initial_text: str = "",
    selected_region=None,
    capture_path: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    on_saved=None,
) -> OverlayWindow:
    return OverlayWindow(
        parent,
        initial_text=initial_text,
        selected_region=selected_region,
        capture_path=capture_path,
        data=data,
        on_saved=on_saved,
    )
