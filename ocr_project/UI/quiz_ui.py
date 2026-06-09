import tkinter as tk
from tkinter import messagebox, ttk

from CORE import db
from CORE.app_settings import load_settings
from CORE.gemini_service import grade_with_optional_gemini
from CORE.study_logic import ProblemLoader, SolverRecordManager


class QuizWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("퀴즈 풀기")
        self.win.geometry("820x560")
        self.win.minsize(560, 360)
        self.win.configure(bg="#f7f8fb")

        self.quiz_items = self._load_quiz_items()
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        self.session = None
        self.record_manager = SolverRecordManager()
        if self.quiz_items:
            first_ocr_id = self.quiz_items[0].get("ocr_result_id")
            self.session = self.record_manager.start_session(first_ocr_id, len(self.quiz_items))

        self._build_ui()
        self._render_question()
        self.win.bind("<Configure>", self._on_window_resized)

    def _build_ui(self) -> None:
        container = tk.Frame(self.win, bg="#f7f8fb", padx=12, pady=10)
        container.pack(fill="both", expand=True)

        top = tk.Frame(container, bg="#f7f8fb")
        top.pack(fill="x")
        tk.Label(top, text="퀴즈 풀기", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.progress_label = tk.Label(top, text="", fg="#555555")
        self.progress_label.pack(side="right")

        q_box = tk.LabelFrame(container, text="문제", padx=10, pady=10)
        q_box.pack(fill="x", pady=(0, 8))
        self.question_var = tk.StringVar()
        self.question_label = tk.Label(q_box, textvariable=self.question_var, justify="left", wraplength=700)
        self.question_label.pack(anchor="w", fill="x")

        a_box = tk.LabelFrame(container, text="답안 입력", padx=10, pady=10)
        a_box.pack(fill="x", pady=(0, 8))
        self.answer_var = tk.StringVar()
        self.answer_entry = tk.Entry(a_box, textvariable=self.answer_var, font=("Segoe UI", 11))
        self.answer_entry.pack(fill="x")

        btns = tk.Frame(container, bg="#f7f8fb", pady=8)
        btns.pack(fill="x")

        tk.Button(
            btns,
            text="정답 체크",
            width=12,
            command=self.check_answer,
            bg="#2d6cdf",
            fg="white",
            activebackground="#2559b7",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            btns,
            text="다음 문제",
            width=12,
            command=self.next_question,
            bg="#e2e2e2",
            relief="flat",
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        self.result_var = tk.StringVar(value="대기 중")
        result_box = tk.LabelFrame(container, text="결과", padx=10, pady=10)
        result_box.pack(fill="both", expand=True)
        self.result_label = tk.Label(
            result_box,
            textvariable=self.result_var,
            fg="#333333",
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self.result_label.pack(fill="both", expand=True)

    def _on_window_resized(self, _event=None) -> None:
        wrap = max(320, self.win.winfo_width() - 100)
        self.question_label.configure(wraplength=wrap)
        self.result_label.configure(wraplength=wrap)

    def _load_quiz_items(self):
        loader = ProblemLoader()
        quiz_items = []
        for row in db.list_ocr_results(limit=20):
            ocr_result_id = row["id"]
            problems = loader.list_for_ocr_result(ocr_result_id)
            if not problems:
                loader.generate_and_store(ocr_result_id)
                problems = loader.list_for_ocr_result(ocr_result_id)
            quiz_items.extend(problems)
        return quiz_items

    def _render_question(self) -> None:
        if not self.quiz_items:
            self.question_var.set("출제할 퀴즈가 없습니다.\n먼저 퀴즈를 생성해 주세요.")
            self.progress_label.config(text="0 / 0")
            return

        q = self.quiz_items[self.current_index]
        self.question_var.set(q.get("question_text", "질문을 불러올 수 없습니다."))
        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.quiz_items)} | 정답 {self.correct_count}/{self.solved_count}"
        )
        self.answer_var.set("")
        self.answer_entry.focus_set()

    def check_answer(self) -> None:
        if not self.quiz_items:
            return

        user_answer = self.answer_var.get().strip()
        if not user_answer:
            messagebox.showwarning("알림", "답안을 입력해 주세요.")
            return

        current_problem = self.quiz_items[self.current_index]
        expected = current_problem.get("answer_text", "").strip()
        if self.session is None:
            messagebox.showerror("오류", "풀이 세션을 시작할 수 없습니다.")
            return

        gemini_fallback = grade_with_optional_gemini if load_settings().gemini_enabled else None
        record = self.record_manager.submit_answer(
            self.session.id,
            int(current_problem["id"]),
            user_answer,
            gemini_fallback=gemini_fallback,
        )
        self.solved_count += 1
        source = "Gemini 검토" if record.judged_by == "gemini" else "기본 채점"
        feedback = f"\n피드백: {record.feedback}" if record.feedback else ""
        if record.final_status == "correct":
            self.correct_count += 1
            self.result_var.set(f"정답입니다. 점수: {record.final_score}\n판정: {source}{feedback}")
        elif record.final_status == "ambiguous":
            self.result_var.set(
                f"애매한 답변입니다. 점수: {record.final_score}\n"
                f"판정: {source}{feedback}\n정답 예시: {expected}"
            )
        else:
            self.result_var.set(f"오답입니다. 점수: {record.final_score}\n판정: {source}{feedback}\n정답: {expected}")

        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.quiz_items)} | 정답 {self.correct_count}/{self.solved_count}"
        )

    def next_question(self) -> None:
        if not self.quiz_items:
            return
        self.current_index = (self.current_index + 1) % len(self.quiz_items)
        self.result_var.set("대기 중")
        self._render_question()


def open_quiz_window(parent: tk.Misc) -> QuizWindow:
    return QuizWindow(parent)
