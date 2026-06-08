import tkinter as tk
from tkinter import messagebox, ttk

from CORE import db
from CORE.study_logic import ProblemLoader, SolverRecordManager


class QuizWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("퀴즈 풀기")
        self.win.geometry("760x460")
        self.win.minsize(560, 360)

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

    def _build_ui(self) -> None:
        top = tk.Frame(self.win, padx=12, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="퀴즈 풀기", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.progress_label = tk.Label(top, text="", fg="#555555")
        self.progress_label.pack(side="right")

        q_box = tk.LabelFrame(self.win, text="문제", padx=10, pady=10)
        q_box.pack(fill="x", padx=12, pady=(0, 8))
        self.question_var = tk.StringVar()
        tk.Label(q_box, textvariable=self.question_var, justify="left", wraplength=700).pack(anchor="w")

        a_box = tk.LabelFrame(self.win, text="답안 입력", padx=10, pady=10)
        a_box.pack(fill="x", padx=12, pady=(0, 8))
        self.answer_var = tk.StringVar()
        self.answer_entry = tk.Entry(a_box, textvariable=self.answer_var, font=("Segoe UI", 11))
        self.answer_entry.pack(fill="x")

        btns = tk.Frame(self.win, padx=12, pady=8)
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
        tk.Label(
            self.win,
            textvariable=self.result_var,
            fg="#333333",
            anchor="w",
            justify="left",
            padx=12,
            pady=8,
        ).pack(fill="x")

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

        record = self.record_manager.submit_answer(self.session.id, int(current_problem["id"]), user_answer)
        self.solved_count += 1
        if record.final_status == "correct":
            self.correct_count += 1
            self.result_var.set(f"정답입니다. 점수: {record.final_score}")
        else:
            self.result_var.set(f"오답입니다. 점수: {record.final_score}\n정답: {expected}")

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
