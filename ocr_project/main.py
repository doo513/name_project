import queue
import sys
import threading
from hashlib import sha1
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from CORE import db
from CORE.app_settings import AppSettings, load_settings
from CORE.ocr_stabilizer import OCRStabilizer, StabilizerConfig
from CORE.ocr_service import OCRService
from CORE.translation_service import TranslationService
from CORE.language_config import (
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    LANGUAGE_CODES,
    get_language_name,
    get_ocr_languages,
    get_translation_language,
)


Region = Tuple[int, int, int, int]


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
        self.settings = load_settings()

        self.capture_interval_seconds = 2.0
        self.capture_padding_pixels = 8
        self.selected_region: Optional[Region] = None
        self.capture_path = None
        self.ocr_text: List[str] = []
        self.last_frame_signature: Optional[str] = None
        self.capture_monitor = None
        self.ocr_service = OCRService()
        self.last_result_languages: List[str] = []
        self.confirmed_source_language: Optional[str] = None
        self.confirmed_target_language: Optional[str] = None

        self.candidate_hold_job: Optional[str] = None
        self.candidate_hold_milliseconds = int(self.settings.ocr_hold_seconds * 1000)
        self.ocr_stabilizer = self._build_ocr_stabilizer(self.settings)

        self.capture_session_id = 0
        self.ocr_in_flight = False
        self.translation_service = TranslationService()
        self.translated_text: Optional[str] = None
        self.translation_in_flight = False
        self.translation_failed = False
        self.translation_request_id = 0
        self.ui_queue: queue.Queue = queue.Queue()
        self.translate_target_var = tk.StringVar(value=DEFAULT_TARGET_LANGUAGE)

        self._build_ui()
        self._poll_ui_queue()

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

        tk.Button(self.root, text="OCR 번역 시작", bg="#5E66F2", command=self.open_selector, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="퀴즈 풀기", bg="#8AA0F2", command=self.open_quiz, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="저장 기록 보기", bg="#99A6F2", command=self.open_study_list, **btn_style).pack(padx=30, fill="x", pady=5)
        tk.Button(self.root, text="설정", bg="#6B7FF2", command=self.open_settings, **btn_style).pack(padx=30, fill="x", pady=5)

    def _build_language_controls(self) -> None:
        frame = tk.Frame(self.root, bg="white")
        frame.pack(pady=(5, 10))
        
        tk.Label(frame, text="원본:", font=("Segoe UI", 9, "bold"), bg="white", fg="#65676B").pack(side="left", padx=(0, 5))
        
        self.source_lang_var = tk.StringVar(value=DEFAULT_SOURCE_LANGUAGE)
        
        self.source_lang_combo = ttk.Combobox(
            frame,
            textvariable=self.source_lang_var,
            values=LANGUAGE_CODES,
            state="readonly",
            width=8,
        )
        self.source_lang_combo.pack(side="left", padx=(0, 8))
        
        tk.Label(frame, text="->", font=("Segoe UI", 10, "bold"), bg="white", fg="#65676B").pack(side="left", padx=8)
        
        tk.Label(frame, text="번역:", font=("Segoe UI", 9, "bold"), bg="white", fg="#65676B").pack(side="left", padx=(0, 5))
        
        self.translate_target_var = tk.StringVar(value=DEFAULT_TARGET_LANGUAGE)
        
        self.translate_target_combo = ttk.Combobox(
            frame,
            textvariable=self.translate_target_var,
            values=LANGUAGE_CODES,
            state="readonly",
            width=8,
        )
        self.translate_target_combo.pack(side="left")

    def _get_language_display(self, code: str) -> str:
        return get_language_name(code)

    def _get_selected_ocr_languages(self) -> List[str]:
        return get_ocr_languages(self._get_current_source_language())

    def _get_current_translation_source_language(self) -> str:
        return get_translation_language(self._get_current_source_language())

    def _get_current_translation_target_language(self) -> str:
        return get_translation_language(self._get_current_target_language())

    def _build_ocr_stabilizer(self, settings: AppSettings) -> OCRStabilizer:
        return OCRStabilizer(
            StabilizerConfig(
                required_matches=settings.ocr_recheck_count,
                similarity_threshold=settings.ocr_similarity_threshold,
            )
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.candidate_hold_milliseconds = int(settings.ocr_hold_seconds * 1000)
        self._reset_candidate_state(cancel_timer=True)
        self.ocr_stabilizer = self._build_ocr_stabilizer(settings)
        self._set_capture_status(
            f"Settings applied: OCR confirmation uses {settings.ocr_recheck_count} sample(s), "
            f"{settings.ocr_hold_seconds:.1f}s hold."
        )

    def _on_region_selected(self, region: Region) -> None:
        monitored_region = self._expand_capture_region(region)
        self.capture_session_id += 1
        self.selected_region = monitored_region
        self.capture_path = None
        self.ocr_text = []
        self.last_result_languages = []
        self.last_frame_signature = None
        self.ocr_in_flight = False
        self.translated_text = None
        self.translation_in_flight = False
        self.translation_failed = False
        self.confirmed_source_language = None
        self.confirmed_target_language = None
        self._reset_candidate_state(cancel_timer=True)

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
        self.translation_service = TranslationService(target=self._get_current_translation_target_language())
        monitor = open_capture_monitor(
            self.root,
            region=region,
            interval_seconds=self.capture_interval_seconds,
            source_lang=self._get_current_source_language(),
            target_lang=self._get_current_target_language(),
            on_frame=lambda selected_region, image, force: self._on_capture_frame(
                session_id,
                selected_region,
                image,
                force,
            ),
            on_save=self._save_current_result,
            on_stop=self._on_capture_stopped,
            on_translate=self._on_translate_pressed,
            on_reselect=self._on_region_selected,
        )
        if monitor is None:
            self._set_capture_status("Capture monitor failed to initialize.")
            self.root.deiconify()
            return

        self.capture_monitor = monitor
        monitor.set_result_text("Waiting for OCR result...")
        monitor.focus_panel()

        started = monitor.start()
        if started is False:
            if self.capture_monitor is monitor:
                self.capture_monitor = None
            backend_error = getattr(monitor, "last_capture_error", None)
            if backend_error:
                self._set_capture_status(f"Capture failed: {backend_error}")
            else:
                self._set_capture_status("Capture failed: no available screen capture backend.")
            if self.root.winfo_exists():
                self.root.deiconify()
                self.root.lift()

    def _on_capture_frame(self, session_id: int, region: Region, image, force: bool = False) -> None:
        if session_id != self.capture_session_id:
            return

        signature = self._make_frame_signature(image)
        if not force and signature == self.last_frame_signature and not self.ocr_stabilizer.needs_sample():
            self._set_capture_status("No visual change in selected region.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("No visual change detected.")
            return

        if signature != self.last_frame_signature and self.candidate_hold_job is not None:
            self._reset_candidate_state(cancel_timer=True)

        if self.ocr_in_flight:
            self._set_capture_status("OCR busy. Waiting for the current run to finish.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("OCR busy. Skipped this frame.")
            return

        self.last_frame_signature = signature
        self._start_ocr_worker(session_id, region, image)

    def _start_ocr_worker(self, session_id: int, region: Region, image) -> None:
        ocr_languages = self._get_selected_ocr_languages()
        source_language = self._get_current_source_language()
        self.ocr_service.set_languages(ocr_languages)
        self.ocr_in_flight = True
        ocr_lang_text = ", ".join(ocr_languages)
        self._set_capture_status(f"Running OCR on the selected region... OCR backend languages: [{ocr_lang_text}]")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(f"Running OCR... [{ocr_lang_text}]")

        def worker() -> None:
            try:
                result = self.ocr_service.recognize_image(image)
                error = None
            except Exception as exc:
                result = []
                error = str(exc)

            self._enqueue_ui(lambda: self._on_ocr_complete(session_id, region, result, error, [source_language]))

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
            self._process_ocr_candidate(result, languages)
        else:
            self._reset_candidate_state(cancel_timer=True)
            self._set_capture_status("No text detected in the selected region.")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("No text detected in the selected region.")
                if not self.ocr_text:
                    self.capture_monitor.set_result_text("No confirmed text detected yet.")

            if not self.ocr_text:
                self._set_preview([])

    def _save_current_result(self) -> None:
        if not self.ocr_text:
            messagebox.showwarning("Notice", "There is no confirmed OCR result to save yet.")
            return
        if not self.selected_region:
            messagebox.showwarning("Notice", "No selected region is available.")
            return

        content = "\n".join(self.ocr_text).strip()
        tags = ",".join(self.last_result_languages or [self._get_current_source_language()])
        translated = self.translated_text
        if self.translation_in_flight:
            messagebox.showwarning("Notice", "Translation is still running. Please save after translation completes.")
            return
        if translated is None:
            messagebox.showwarning("Notice", "Translation is not ready. Please translate the confirmed text before saving.")
            return

        try:
            row_id = db.save_json_record(
                content=content,
                source_region=str(self.selected_region),
                tags=tags,
                translation=translated,
                source_language=self.confirmed_source_language,
                target_language=self.confirmed_target_language or self._get_current_target_language(),
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save OCR result.\n{exc}")
            return

        self._set_capture_status(f"Saved OCR result #{row_id} to the database.")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(f"Saved OCR result #{row_id}.")
        messagebox.showinfo("Saved", f"Saved OCR result #{row_id} to SQLite.")

    def _on_translate_pressed(self) -> None:
        if not self.ocr_text:
            messagebox.showwarning("Notice", "There is no confirmed OCR text to translate yet.")
            return

        self._start_translation_for_confirmed_text()

    def _on_translate_complete(
        self,
        request_id: int,
        source_text: str,
        result: Optional[str],
        error: Optional[str],
        target_lang: str,
        source_lang: str,
    ) -> None:
        if request_id != self.translation_request_id or source_text != "\n".join(self.ocr_text).strip():
            return

        if error:
            self.translation_in_flight = False
            self.translation_failed = True
            self._set_capture_status(f"Translation failed: {error}")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status(f"Translation failed: {error}")
            return

        if result and result.strip():
            self.translated_text = result.strip()
            self.translation_in_flight = False
            self.translation_failed = False
            display_text = f"{source_lang} -> {target_lang}:\n{source_text}\n\n-> {self.translated_text}"
            self._set_capture_status(f"Translated {source_lang} -> {target_lang}")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status(f"Translated {source_lang} -> {target_lang}")
                self.capture_monitor.set_result_text(display_text)
        else:
            self.translation_in_flight = False
            self.translation_failed = True
            self._set_capture_status("Translation failed")
            if self.capture_monitor is not None:
                self.capture_monitor.set_status("Translation failed")

    def _on_capture_stopped(self) -> None:
        self._reset_candidate_state(cancel_timer=True)
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

    def _process_ocr_candidate(self, lines: List[str], languages: List[str]) -> None:
        decision = self.ocr_stabilizer.submit(lines, languages)
        if decision.should_cancel_hold:
            self._cancel_candidate_hold_job()

        if not decision.status:
            self._reset_candidate_state(cancel_timer=True)
            return

        if decision.should_start_hold:
            self._schedule_candidate_confirmation()

        self._set_capture_status(decision.status)
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(decision.status)
            if not self.ocr_text:
                self.capture_monitor.set_result_text("Stabilizing OCR text...")

    def _schedule_candidate_confirmation(self) -> None:
        if self.candidate_hold_job is not None:
            return
        normalized = self.ocr_stabilizer.start_hold()
        if not normalized:
            return
        self.candidate_hold_job = self.root.after(
            self.candidate_hold_milliseconds,
            lambda: self._confirm_candidate_if_stable(normalized),
        )

    def _confirm_candidate_if_stable(self, expected_normalized: str) -> None:
        self.candidate_hold_job = None
        confirmed = self.ocr_stabilizer.confirm_if_stable(expected_normalized)
        if confirmed is None:
            return

        confirmed_text = confirmed.text
        if confirmed_text == "\n".join(self.ocr_text).strip():
            return

        self.ocr_text = confirmed_text.splitlines()
        self.last_result_languages = list(confirmed.languages)
        self.confirmed_source_language = self.last_result_languages[0] if self.last_result_languages else None
        self.confirmed_target_language = self._get_current_target_language()
        self.translated_text = None
        self.translation_in_flight = False
        self.translation_failed = False
        self._set_preview(self.ocr_text)
        self._set_capture_status("OCR text confirmed. Translating automatically...")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status("OCR text confirmed. Translating automatically...")
            self.capture_monitor.set_result_text(confirmed_text)
        self._start_translation_for_confirmed_text()

    def _reset_candidate_state(self, cancel_timer: bool) -> None:
        if cancel_timer:
            self._cancel_candidate_hold_job()
        self.ocr_stabilizer.reset()

    def _get_current_target_language(self) -> str:
        if self.capture_monitor is not None:
            return self.capture_monitor.get_translate_target()
        return self.translate_target_var.get()

    def _get_current_source_language(self) -> str:
        if self.capture_monitor is not None:
            return self.capture_monitor.get_source_lang()
        return self.source_lang_var.get()

    def _start_translation_for_confirmed_text(self) -> None:
        original_text = "\n".join(self.ocr_text).strip()
        if not original_text:
            return

        source_lang = self._get_current_translation_source_language()
        target_lang = self._get_current_translation_target_language()
        self.confirmed_source_language = self._get_current_source_language()
        self.confirmed_target_language = self._get_current_target_language()
        self.translation_request_id += 1
        request_id = self.translation_request_id

        self.translation_service.set_source_language(source_lang)
        self.translation_service.set_target_language(target_lang)
        self.translation_in_flight = True
        self.translation_failed = False
        self.translated_text = None

        self._set_capture_status(f"Translating confirmed text {source_lang} -> {target_lang}...")
        if self.capture_monitor is not None:
            self.capture_monitor.set_status(f"Translating confirmed text {source_lang} -> {target_lang}...")

        def worker() -> None:
            try:
                result = self.translation_service.translate(original_text)
                error = None
            except Exception as exc:
                result = None
                error = str(exc)

            self._enqueue_ui(
                lambda: self._on_translate_complete(
                    request_id,
                    original_text,
                    result,
                    error,
                    target_lang,
                    source_lang,
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _cancel_candidate_hold_job(self) -> None:
        if self.candidate_hold_job is not None:
            self.root.after_cancel(self.candidate_hold_job)
            self.candidate_hold_job = None

    def _enqueue_ui(self, callback) -> None:
        self.ui_queue.put(callback)

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                callback = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        self.root.after(50, self._poll_ui_queue)

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

    def open_study_list(self) -> None:
        try:
            from UI.study_list import open_study_list_window

            open_study_list_window(self.root)
        except ImportError:
            self._open_placeholder("Study List", "study_list.py or open_study_list_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open study list window.\n{exc}")

    def open_settings(self) -> None:
        try:
            from UI.settings_ui import open_settings_window

            open_settings_window(self.root, on_saved=self._apply_settings)
        except ImportError:
            self._open_placeholder("Settings", "settings_ui.py or open_settings_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open settings window.\n{exc}")

    def open_quiz(self) -> None:
        try:
            from UI.quiz_ui import open_quiz_window

            open_quiz_window(self.root)
        except ImportError:
            self._open_placeholder("Quiz", "quiz_ui.py or open_quiz_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open quiz window.\n{exc}")

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
