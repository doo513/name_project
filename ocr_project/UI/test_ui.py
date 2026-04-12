import random
import tkinter as tk
from tkinter import messagebox

from CORE import db


class TestWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("테스트 UI")
        self.win.geometry("760x460")
        self.win.minsize(560, 360)

        self.questions = self._load_questions()
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0

        self._build_ui()
        self._render_question()

    def _build_ui(self) -> None:
        top = tk.Frame(self.win, padx=12, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="복습 테스트", font=("Segoe UI", 12, "bold")).pack(side="left")
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

    def _load_questions(self):
        rows = db.list_ocr_results(limit=100)
        questions = []

        for row in rows:
            content = (row.get("content") or "").strip()
            if not content:
                continue
            questions.append(
                {
                    "question": f"다음 OCR 결과를 그대로 입력하세요:\n\n{content}",
                    "answer": content,
                    "meta": f"ID {row['id']}",
                }
            )

        if not questions:
            questions = [
                {"question": "문제 1) '서울역'을 그대로 입력하세요.", "answer": "서울역", "meta": "더미"},
                {"question": "문제 2) '12,500원'을 그대로 입력하세요.", "answer": "12,500원", "meta": "더미"},
                {"question": "문제 3) '2026-04-04'를 그대로 입력하세요.", "answer": "2026-04-04", "meta": "더미"},
            ]

        random.shuffle(questions)
        return questions

    def _render_question(self) -> None:
        if not self.questions:
            self.question_var.set("출제할 문제가 없습니다.")
            self.progress_label.config(text="0 / 0")
            return

        q = self.questions[self.current_index]
        self.question_var.set(q["question"])
        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.questions)} | 정답 {self.correct_count}/{self.solved_count}"
        )
        self.answer_var.set("")
        self.answer_entry.focus_set()

    def check_answer(self) -> None:
        if not self.questions:
            return

        user_answer = self.answer_var.get().strip()
        if not user_answer:
            messagebox.showwarning("알림", "답안을 입력해 주세요.")
            return

        expected = self.questions[self.current_index]["answer"].strip()
        self.solved_count += 1

        if user_answer == expected:
            self.correct_count += 1
            self.result_var.set("정답입니다.")
        else:
            self.result_var.set(f"오답입니다. 정답: {expected}")

        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.questions)} | 정답 {self.correct_count}/{self.solved_count}"
        )

    def next_question(self) -> None:
        if not self.questions:
            return
        self.current_index = (self.current_index + 1) % len(self.questions)
        self.result_var.set("대기 중")
        self._render_question()


def open_test_window(parent: tk.Misc) -> TestWindow:
    return TestWindow(parent)
