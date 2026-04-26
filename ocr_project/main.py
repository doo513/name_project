import sys
import threading
from hashlib import sha1
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from CORE import db
from CORE.ocr_service import OCRService
from CORE.translation_service import TranslationService


Region = Tuple[int, int, int, int]
LANGUAGE_OPTIONS = [
    ("Korean", "ko"),
    ("English", "en"),
    ("Japanese", "ja"),
    ("Chinese Simplified", "ch_sim"),
    ("Chinese Traditional", "ch_tra"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Russian", "ru"),
    ("Arabic", "ar"),
]
LANGUAGE_CODE_TO_NAME = {code: name for name, code in LANGUAGE_OPTIONS}


def _enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class MainApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OCR Integrated Study App")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        self.root.minsize(500, 400)

        self.capture_interval_seconds = 2.0
        self.capture_padding_pixels = 8
        self.selected_region: Optional[Region] = None
        self.capture_path = None
        self.ocr_text: List[str] = []
        self.last_frame_signature: Optional[str] = None
        self.capture_monitor = None
        self.ocr_service = OCRService()
        self.last_result_languages: List[str] = []

        self.capture_session_id = 0
        self.ocr_in_flight = False
        self.translation_service = TranslationService()
        self.translated_text = None
        self.translate_target_var = tk.StringVar(value="ko")

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#4B4FA6", height=100)
        header.pack(fill="x")
        tk.Label(header, text="OCR Study App", font=("Segoe UI", 18, "bold"), bg="#4B4FA6", fg="white").pack(pady=30)

        card = tk.Frame(self.root, bg="white", highlightthickness=1, highlightbackground="#DDDDDD")
        card.pack(padx=30, pady=20, fill="x")

        self._build_language_controls()

        self.region_label_var = tk.StringVar(value="Selected Region: None")
        self.status_label_var = tk.StringVar(value="Ready for Scanning")
        self.preview_label_var = tk.StringVar(value="OCR Preview: None")

        tk.Label(card, text="SYSTEM STATUS", font=("Segoe UI", 8, "bold"), bg="white", fg="#65676B").pack(pady=(15, 0), padx=20, anchor="w")
        tk.Label(card, textvariable=self.status_label_var, font=("Segoe UI", 12, "bold"), bg="white", fg="#1C1E21").pack(pady=(5, 10), padx=20, anchor="w")
        tk.Label(card, textvariable=self.region_label_var, font=("Segoe UI", 9), bg="white", fg="#8A8D91").pack(padx=20, anchor="w")
        tk.Label(card, textvariable=self.preview_label_var, font=("Segoe UI", 8), bg="white", fg="#8A8D91", wraplength=350, justify="left").pack(pady=(5, 15), padx=20, anchor="w")

        btn_style = {"font": ("Segoe UI", 10, "bold"), "fg": "white", "relief": "flat", "height": 2, "cursor": "hand2"}

        tk.Button(self.root, text="Open Region Selector", bg="#5E66F2", command=self.open_selector, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="Open Overlay", bg="#6B7FF2", command=self.open_capture_panel, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="Open Study List", bg="#99A6F2", command=self.open_study_list, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="Open Test UI", bg="#B3BDF2", command=self.open_test_ui, **btn_style).pack(padx=30, fill="x", pady=5)

    def _build_language_controls(self) -> None:
        frame = tk.Frame(self.root, bg="white")
        frame.pack(pady=(5, 10))
        
        tk.Label(frame, text="원본:", font=("Segoe UI", 9, "bold"), bg="white", fg="#65676B").pack(side="left", padx=(0, 5))
        
        self.source_lang_var = tk.StringVar(value="en")
        
        self.source_lang_combo = ttk.Combobox(
            frame,
            textvariable=self.source_lang_var,
            values=["ko", "en", "ja", "zh", "es", "fr", "de", "ru", "ar"],
            state="readonly",
            width=8,
        )
        self.source_lang_combo.pack(side="left", padx=(0, 8))
        
        tk.Label(frame, text="->", font=("Segoe UI", 10, "bold"), bg="white", fg="#65676B").pack(side="left", padx=8)
        
        tk.Label(frame, text="번역:", font=("Segoe UI", 9, "bold"), bg="white", fg="#65676B").pack(side="left", padx=(0, 5))
        
        self.translate_target_var = tk.StringVar(value="ko")
        
        self.translate_target_combo = ttk.Combobox(
            frame,
            textvariable=self.translate_target_var,
            values=["ko", "en", "ja", "zh", "es", "fr", "de", "ru", "ar"],
            state="readonly",
            width=8,
        )
        self.translate_target_combo.pack(side="left")

    def _get_language_display(self, code: str) -> str:
        name = LANGUAGE_CODE_TO_NAME.get(code, code.upper())
        return f"{name}"

    def _get_selected_language_codes(self) -> List[str]:
        if self.capture_monitor is not None:
            return [self.capture_monitor.get_source_lang(), self.capture_monitor.get_translate_target()]
        return [self.source_lang_var.get(), self.translate_target_var.get()]

    def _on_region_selected(self, region: Region) -> None:
        monitored_region = self._expand_capture_region(region)
        self.capture_session_id += 1
        self.selected_region = monitored_region
        self.capture_path = None
        self.ocr_text = []
        self.last_result_languages = []
        self.last_frame_signature = None
        self.ocr_in_flight = False

        self.region_label_var.set(f"Monitoring Region: {monitored_region}")
        self._set_capture_status(
            f"Monitoring selected region every {self.capture_interval_seconds:.1f} seconds "
            f"with {self.capture_padding_pixels}px edge padding."
        )
        self._set_preview([])

        self.root.iconify()
        self._start_capture_monitor(monitored_region)

    def _start_capture_monitor(self, region: Region) -> None:
        if self.capture_monitor is not None:
            self.capture_monitor.stop(notify=False)
            self.capture_monitor = None

        try:
            from UI.capture_monitor import open_capture_monitor
        except ImportError as exc:
            messagebox.showerror("Error", f"Failed to load capture monitor.\n{exc}")
            return

        session_id = self.capture_session_id
        self.translation_service = TranslationService(target=self.translate_target_var.get())
        self.capture_monitor = open_capture_monitor(
            self.root,
            region=region,
            interval_seconds=self.capture_interval_seconds,
            on_frame=lambda selected_region, image, force: self._on_capture_frame(
                session_id,
                selected_region,
                image,
                force,
            ),
            on_save=self._save_current_result,
            on_stop=self._on_capture_stopped,
            on_translate=self._on_translate_pressed,
        )
        self.capture_monitor.start()
        self.capture_monitor.set_result_text("Waiting for OCR result...")
        self.capture_monitor.focus_panel()

    def _on_capture_frame(self, session_id: int, region: Region, image, force: bool = False) -> None:
        if session_id != self.capture_session_id:
            return

        signature = self._make_frame_signature(image)
        if not force and signature == self.last_frame_signature:
            self._set_capture_status("No visual change in selected region.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("No visual change detected.")
            return

        if self.ocr_in_flight:
            self._set_capture_status("OCR busy. Waiting for the current run to finish.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("OCR busy. Skipped this frame.")
            return

        self.last_frame_signature = signature
        self._start_ocr_worker(session_id, region, image)

    def _start_ocr_worker(self, session_id: int, region: Region, image) -> None:
        selected_languages = self._get_selected_language_codes()
        self.ocr_service.set_languages(selected_languages)
        self.ocr_in_flight = True
        self._set_capture_status("Running OCR on the selected region...")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status("Running OCR...")

        def worker() -> None:
            try:
                raw_result = self.ocr_service.recognize_image_raw(image)
                print(f"DEBUG OCR raw: {raw_result}")
                result = self.ocr_service.recognize_image(image)
                print(f"DEBUG OCR cleaned: {result}")
                error = None
            except Exception as exc:
                result = []
                error = str(exc)

            self.root.after(
                0,
                lambda: self._on_ocr_complete(session_id, region, result, error, selected_languages),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_ocr_complete(
        self,
        session_id: int,
        region: Region,
        result: List[str],
        error: Optional[str],
        languages: List[str],
    ) -> None:
        if session_id != self.capture_session_id:
            return

        self.ocr_in_flight = False

        if error:
            self._set_capture_status(f"OCR failed: {error}")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status(f"OCR failed: {error}")
                self.capture_monitor.set_result_text(f"OCR failed:\n{error}")
            return

        if result:
            self.ocr_text = list(result)
            self.last_result_languages = list(languages)
            current_text = self.ocr_text
            self._set_capture_status(f"OCR updated. {len(result)} line(s) detected in the region.")
            self._set_preview(current_text)

            if self.capture_monitor is not None:
                self.capture_monitor.set_status("OCR updated from the latest capture.")
                self.capture_monitor.set_result_text("\n".join(current_text))
        else:
            self.ocr_text = []
            self.last_result_languages = []
            self._set_capture_status("No text detected in the selected region.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("No text detected in the selected region.")
                self.capture_monitor.set_result_text("No text detected.")

            self._set_preview([])

    def _save_current_result(self) -> None:
        if not self.ocr_text:
            messagebox.showwarning("Notice", "There is no OCR result to save.")
            return
        if not self.selected_region:
            messagebox.showwarning("Notice", "No selected region is available.")
            return

        content = "\n".join(self.ocr_text).strip()
        tags = ",".join(self.last_result_languages or self._get_selected_language_codes())
        translated = self.translated_text

        try:
            row_id = db.save_json_record(
                content=content,
                source_region=str(self.selected_region),
                tags=tags,
                translation=translated,
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save OCR result.\n{exc}")
            return

        self._set_capture_status(f"Saved OCR result #{row_id} to the database.")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(f"Saved OCR result #{row_id}.")
        messagebox.showinfo("Saved", f"Saved OCR result #{row_id} as JSON in the database.")

    def _on_translate_pressed(self) -> None:
        if not self.ocr_text:
            messagebox.showwarning("Notice", "There is no OCR text to translate.")
            return

        original_text = "\n".join(self.ocr_text)
        
        if self.capture_monitor is not None:
            source_lang = self.capture_monitor.get_source_lang()
            target_lang = self.capture_monitor.get_translate_target()
        else:
            source_lang = self.source_lang_var.get()
            target_lang = self.translate_target_var.get()

        self.translation_service.set_source_language(source_lang)
        self.translation_service.set_target_language(target_lang)

        self._set_capture_status(f"Translating {source_lang} -> {target_lang}...")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(f"Translating {source_lang} -> {target_lang}...")

        def worker() -> None:
            try:
                result = self.translation_service.translate(original_text)
                error = None
            except Exception as exc:
                result = None
                error = str(exc)

            self.root.after(0, lambda: self._on_translate_complete(result, error, target_lang, source_lang))

        threading.Thread(target=worker, daemon=True).start()

    def _on_translate_complete(self, result: Optional[str], error: Optional[str], target_lang: str, source_lang: str) -> None:
        if error:
            self._set_capture_status(f"Translation failed: {error}")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status(f"Translation failed: {error}")
            messagebox.showerror("Translation Error", error)
            return

        original = "\n".join(self.ocr_text)
        
        if result and result.strip():
            self.translated_text = result
            display_text = f"{source_lang} -> {target_lang}:\n{original}\n\n-> {result}"
            self._set_capture_status(f"Translated {source_lang} -> {target_lang}")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status(f"Translated {source_lang} -> {target_lang}")
                self.capture_monitor.set_result_text(display_text)
        else:
            self._set_capture_status("Translation failed")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("Translation failed")
            messagebox.showwarning("Translation Warning", "번역 결과를 가져올 수 없습니다.")

    def _on_capture_stopped(self) -> None:
        self.capture_monitor = None
        self.ocr_in_flight = False
        self.capture_session_id += 1
        self._set_capture_status("Capture stopped.")
        if self.root.winfo_exists():
            self.root.deiconify()
            self.root.lift()

    def _make_frame_signature(self, image) -> str:
        sample = image.convert("L").resize((32, 32))
        return sha1(sample.tobytes()).hexdigest()

    def _expand_capture_region(self, region: Region) -> Region:
        x1, y1, x2, y2 = region
        padding = self.capture_padding_pixels
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        left = max(0, x1 - padding)
        top = max(0, y1 - padding)
        right = min(screen_width, x2 + padding + 1)
        bottom = min(screen_height, y2 + padding + 1)
        return (left, top, right, bottom)

    def _set_capture_status(self, text: str) -> None:
        self.status_label_var.set(f"Capture Status: {text}")

    def _set_preview(self, lines: List[str]) -> None:
        if not lines:
            self.preview_label_var.set("OCR Preview: None")
            return

        preview = "\n".join(lines)
        truncated = preview[:120] + ("..." if len(preview) > 120 else "")
        self.preview_label_var.set(f"OCR Preview: {truncated}")

    def open_selector(self) -> None:
        try:
            from UI.selector import open_selector_window

            open_selector_window(self.root, on_selected=self._on_region_selected)
        except ImportError:
            self._open_placeholder("Selector", "selector.py or open_selector_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open selector window.\n{exc}")

    def open_capture_panel(self) -> None:
        if self.capture_monitor is None:
            messagebox.showinfo("Notice", "Open Region Selector first to start capture.")
            return

        self.capture_monitor.focus_panel()

    def open_study_list(self) -> None:
        try:
            from UI.study_list import open_study_list_window

            open_study_list_window(self.root)
        except ImportError:
            self._open_placeholder("Study List", "study_list.py or open_study_list_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open study list window.\n{exc}")

    def open_test_ui(self) -> None:
        try:
            from UI.test_ui import open_test_window

            open_test_window(self.root)
        except ImportError:
            self._open_placeholder("Test UI", "test_ui.py or open_test_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open test window.\n{exc}")

    def _open_placeholder(self, title: str, message: str) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("380x180")
        win.resizable(False, False)

        tk.Label(win, text=title, font=("Segoe UI", 13, "bold")).pack(pady=(20, 10))
        tk.Label(win, text=message, font=("Segoe UI", 10), fg="#444444", wraplength=330).pack(pady=(0, 16))
        tk.Button(win, text="Close", command=win.destroy, width=12).pack()


def main() -> None:
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
