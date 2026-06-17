import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from CORE.app_settings import AppSettings, load_settings, save_settings, settings_status
from CORE.gemini_service import GeminiService


class SettingsWindow:
    def __init__(self, parent: tk.Misc, on_saved: Optional[Callable[[AppSettings], None]] = None) -> None:
        self.parent = parent
        self.on_saved = on_saved
        self.settings = load_settings()

        self.win = tk.Toplevel(parent)
        self.win.title("설정")
        self.win.geometry("520x430")
        self.win.minsize(460, 380)
        self.win.configure(bg="#f7f8fb")

        self.recheck_count_var = tk.IntVar(value=self.settings.ocr_recheck_count)
        self.hold_seconds_var = tk.DoubleVar(value=self.settings.ocr_hold_seconds)
        self.similarity_var = tk.DoubleVar(value=self.settings.ocr_similarity_threshold)
        self.gemini_key_var = tk.StringVar(value=self.settings.gemini_api_key)
        self.status_var = tk.StringVar(value=self._status_text())

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.win, bg="#f7f8fb", padx=18, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="앱 설정",
            font=("Segoe UI", 16, "bold"),
            bg="#f7f8fb",
            fg="#202124",
        ).pack(anchor="w")
        tk.Label(
            container,
            text="OCR 안정화와 선택 기능인 Gemini API를 관리합니다.",
            font=("Segoe UI", 9),
            bg="#f7f8fb",
            fg="#5f6368",
        ).pack(anchor="w", pady=(2, 14))

        self._build_ocr_section(container)
        self._build_gemini_section(container)
        self._build_actions(container)

    def _build_ocr_section(self, parent: tk.Misc) -> None:
        box = tk.LabelFrame(parent, text="OCR 안정화", padx=12, pady=10, bg="#ffffff")
        box.pack(fill="x", pady=(0, 12))

        row1 = tk.Frame(box, bg="#ffffff")
        row1.pack(fill="x", pady=(0, 8))
        tk.Label(row1, text="재검토 횟수", bg="#ffffff", width=16, anchor="w").pack(side="left")
        ttk.Spinbox(row1, from_=1, to=5, textvariable=self.recheck_count_var, width=8).pack(side="left")
        tk.Label(row1, text="회", bg="#ffffff", fg="#5f6368").pack(side="left", padx=(4, 0))

        row2 = tk.Frame(box, bg="#ffffff")
        row2.pack(fill="x", pady=(0, 8))
        tk.Label(row2, text="확정 대기 시간", bg="#ffffff", width=16, anchor="w").pack(side="left")
        ttk.Spinbox(row2, from_=0.5, to=10.0, increment=0.5, textvariable=self.hold_seconds_var, width=8).pack(side="left")
        tk.Label(row2, text="초", bg="#ffffff", fg="#5f6368").pack(side="left", padx=(4, 0))

        row3 = tk.Frame(box, bg="#ffffff")
        row3.pack(fill="x")
        tk.Label(row3, text="유사도 기준", bg="#ffffff", width=16, anchor="w").pack(side="left")
        ttk.Spinbox(row3, from_=0.5, to=1.0, increment=0.01, textvariable=self.similarity_var, width=8).pack(side="left")
        tk.Label(row3, text="높을수록 엄격합니다", bg="#ffffff", fg="#5f6368").pack(side="left", padx=(8, 0))

    def _build_gemini_section(self, parent: tk.Misc) -> None:
        box = tk.LabelFrame(parent, text="Gemini API (선택 사항)", padx=12, pady=10, bg="#ffffff")
        box.pack(fill="x", pady=(0, 12))

        tk.Label(
            box,
            text="Gemini API 키는 필수가 아닙니다. 키가 없으면 기본 채점으로 동작하고, 문제/채점 품질만 낮아질 수 있습니다.",
            bg="#ffffff",
            fg="#5f6368",
            wraplength=450,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        key_row = tk.Frame(box, bg="#ffffff")
        key_row.pack(fill="x", pady=(0, 8))
        tk.Label(key_row, text="API 키", bg="#ffffff", width=10, anchor="w").pack(side="left")
        tk.Entry(key_row, textvariable=self.gemini_key_var, show="*", width=44).pack(side="left", fill="x", expand=True)

        tk.Label(box, textvariable=self.status_var, bg="#ffffff", fg="#2d6cdf", justify="left").pack(anchor="w")

        tk.Button(
            box,
            text="연결 확인",
            command=self.test_gemini,
            bg="#4B4FA6",
            fg="white",
            relief="flat",
            cursor="hand2",
        ).pack(anchor="e", pady=(8, 0))

    def _build_actions(self, parent: tk.Misc) -> None:
        actions = tk.Frame(parent, bg="#f7f8fb")
        actions.pack(fill="x", pady=(4, 0))
        tk.Button(actions, text="닫기", width=10, command=self.win.destroy).pack(side="right")
        tk.Button(
            actions,
            text="저장",
            width=10,
            command=self.save,
            bg="#2a9d5b",
            fg="white",
            relief="flat",
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

    def _current_settings(self) -> Optional[AppSettings]:
        try:
            recheck_count = self.recheck_count_var.get()
            hold_seconds = self.hold_seconds_var.get()
            similarity = self.similarity_var.get()
        except tk.TclError:
            messagebox.showwarning(
                "설정 확인",
                "OCR 재검토 횟수, 확정 대기 시간, 유사도 기준은 숫자로 입력해 주세요.",
            )
            return None

        return AppSettings(
            ocr_recheck_count=recheck_count,
            ocr_hold_seconds=hold_seconds,
            ocr_similarity_threshold=similarity,
            gemini_api_key=self.gemini_key_var.get(),
        )

    def _sync_vars_from_settings(self) -> None:
        self.recheck_count_var.set(self.settings.ocr_recheck_count)
        self.hold_seconds_var.set(self.settings.ocr_hold_seconds)
        self.similarity_var.set(self.settings.ocr_similarity_threshold)
        self.gemini_key_var.set(self.settings.gemini_api_key)

    def _status_text(self) -> str:
        status = settings_status()
        gemini = "설정됨" if status["gemini_enabled"] else "미설정"
        return f"현재 Gemini 상태: {gemini}\n설정 저장 위치: {status['settings_path']}"

    def save(self) -> None:
        settings = self._current_settings()
        if settings is None:
            return
        save_settings(settings)
        self.settings = load_settings()
        self._sync_vars_from_settings()
        self.status_var.set(self._status_text())
        if callable(self.on_saved):
            self.on_saved(self.settings)
        messagebox.showinfo("저장됨", "설정을 저장하고 현재 앱에 반영했습니다.")

    def test_gemini(self) -> None:
        settings = self._current_settings()
        if settings is None:
            return
        save_settings(settings)
        self.settings = load_settings()
        self._sync_vars_from_settings()
        if callable(self.on_saved):
            self.on_saved(self.settings)
        result = GeminiService(self.settings.gemini_api_key).test_connection()
        self.status_var.set(self._status_text())
        messagebox.showinfo("Gemini 연결 확인", result)


def open_settings_window(parent: tk.Misc, on_saved: Optional[Callable[[AppSettings], None]] = None) -> SettingsWindow:
    return SettingsWindow(parent, on_saved=on_saved)
