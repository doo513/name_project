import importlib
import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from CORE import db
from CORE.app_settings import load_settings
from CORE.gemini_service import grade_with_optional_gemini
from CORE.study_logic import ProblemLoader, SolverRecordManager
from CORE.study_logic.study_repository import StudyRepository


def _call_gemini(prompt: str, api_key: str) -> tuple:
    try:
        genai = importlib.import_module("google.genai")
    except Exception:
        return None, "google-genai 패키지가 설치되지 않았습니다. pip install google-genai 를 실행해 주세요."
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (getattr(response, "text", "") or "").strip()
        return text, None
    except Exception as exc:
        err = str(exc)
        print(f"[Gemini] 호출 실패: {err}")
        return None, err


def _extract_json(text: str) -> Optional[Any]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("[") if "[" in cleaned else cleaned.find("{")
    if start == -1:
        return None
    if cleaned[start] == "[":
        end = cleaned.rfind("]")
    else:
        end = cleaned.rfind("}")
    if end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def generate_problems_with_gemini(
    ocr_result_id: int,
    problem_mode: str,
    api_key: str,
) -> List[Dict[str, Any]]:
    row = db.get_ocr_result(ocr_result_id)
    if not row:
        return []

    source_text = (row.get("content") or "").strip()
    translation_text = (row.get("translation_text") or "").strip()
    if not source_text:
        return []

    if problem_mode == "subjective":
        prompt = f"""
You are a language quiz generator.
Given the following source text (and optional translation), generate 3 quiz questions in JSON array format.

Source text: {source_text}
Translation (if any): {translation_text}

Rules:
- Mix question languages and answer languages freely.
  Some questions can be asked in Korean and answered in English.
  Some can be asked in English and answered in Korean.
  Some can be in the same language.
- Each question must clearly state what language the answer should be in,
  e.g. "(답을 한국어로 쓰세요)" or "(Answer in English)".
- At least 1 of the 3 questions must be a fill-in-the-blank question with problem_type "fill_blank".
  For fill_blank questions, the question_text must contain ____ where the blank is (e.g. "apple ____ banana").
  The answer_text is the word or phrase that fills the blank.
  Do NOT add language instruction for fill_blank questions.
- The remaining questions must have problem_type "subjective".
- explanation_text must be written in Korean (한국어) regardless of the question language.

Return ONLY a JSON array. Each element:
{{
  "problem_type": "subjective" or "fill_blank",
  "question_text": "...",
  "answer_text": "...",
  "acceptable_answers": ["...", "..."],
  "difficulty": "easy|medium|hard",
  "hint_text": "...",
  "explanation_text": "한국어 해설"
}}
"""
    else:
        prompt = f"""
You are a language quiz generator.
Given the following source text (and optional translation), generate 3 quiz questions in JSON array format.

Source text: {source_text}
Translation (if any): {translation_text}

Rules:
- Mix question languages and answer languages freely.
  Some questions can be in Korean with English answer options.
  Some can be in English with Korean answer options.
  Some can be in the same language.
- Each question must clearly state what language the answer should be in.
- At least 1 of the 3 questions must be a fill-in-the-blank question with problem_type "fill_blank".
  For fill_blank questions, the question_text must contain ____ where the blank is (e.g. "apple ____ banana").
  The answer_text is the word or phrase that fills the blank.
  acceptable_answers lists acceptable answer variations.
  fill_blank questions do NOT need options or correct_answers fields.
- The remaining questions must have problem_type "objective_single" or "objective_multi".
  Each objective question must have exactly 5 options.
  objective_single has 1 correct answer (multi_answer: false).
  objective_multi has 2~3 correct answers (multi_answer: true).
  correct_answers is a list of the correct option strings.
- explanation_text must be written in Korean (한국어) regardless of the question language.

Return ONLY a JSON array. Each element:
{{
  "problem_type": "objective_single" or "objective_multi" or "fill_blank",
  "question_text": "...",
  "answer_text": "...(for fill_blank only)",
  "acceptable_answers": ["...(for fill_blank only)"],
  "options": ["option1", "option2", "option3", "option4", "option5 (for objective only)"],
  "correct_answers": ["option1 (for objective only)"],
  "multi_answer": false,
  "difficulty": "easy|medium|hard",
  "hint_text": "...",
  "explanation_text": "한국어 해설"
}}
"""

    raw, err = _call_gemini(prompt, api_key)
    if err:
        raise RuntimeError(err)
    parsed = _extract_json(raw) if raw else None
    if not isinstance(parsed, list):
        raise RuntimeError(f"Gemini 응답을 JSON으로 파싱하지 못했습니다.\n응답 내용: {(raw or '')[:200]}")

    repo = StudyRepository()
    result_problems: List[Dict[str, Any]] = []

    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            if problem_mode == "subjective":
                item_ptype = item.get("problem_type", "subjective")
                if item_ptype == "fill_blank":
                    problem_id = repo.create_problem(
                        ocr_result_id=ocr_result_id,
                        problem_type="fill_blank",
                        question_text=str(item.get("question_text", "")),
                        source_text=source_text,
                        answer_text=str(item.get("answer_text", "")),
                        acceptable_answers=list(item.get("acceptable_answers") or [item.get("answer_text", "")]),
                        keyword_rules={"required_any": [], "required_all": []},
                        difficulty=str(item.get("difficulty", "medium")),
                        hint_text=item.get("hint_text"),
                        explanation_text=item.get("explanation_text"),
                        choice_options=None,
                    )
                else:
                    problem_id = repo.create_problem(
                        ocr_result_id=ocr_result_id,
                        problem_type="subjective",
                        question_text=str(item.get("question_text", "")),
                        source_text=source_text,
                        answer_text=str(item.get("answer_text", "")),
                        acceptable_answers=list(item.get("acceptable_answers") or [item.get("answer_text", "")]),
                        keyword_rules={"required_any": [], "required_all": []},
                        difficulty=str(item.get("difficulty", "medium")),
                        hint_text=item.get("hint_text"),
                        explanation_text=item.get("explanation_text"),
                        choice_options=None,
                    )
            else:
                item_ptype = item.get("problem_type", "objective_single")
                if item_ptype == "fill_blank":
                    problem_id = repo.create_problem(
                        ocr_result_id=ocr_result_id,
                        problem_type="fill_blank",
                        question_text=str(item.get("question_text", "")),
                        source_text=source_text,
                        answer_text=str(item.get("answer_text", "")),
                        acceptable_answers=list(item.get("acceptable_answers") or [item.get("answer_text", "")]),
                        keyword_rules={"required_any": [], "required_all": []},
                        difficulty=str(item.get("difficulty", "medium")),
                        hint_text=item.get("hint_text"),
                        explanation_text=item.get("explanation_text"),
                        choice_options=None,
                    )
                else:
                    options: List[str] = list(item.get("options") or [])
                    correct_answers: List[str] = list(item.get("correct_answers") or [])
                    multi = bool(item.get("multi_answer", False))
                    ptype = "objective_multi" if multi else "objective_single"
                    problem_id = repo.create_problem(
                        ocr_result_id=ocr_result_id,
                        problem_type=ptype,
                        question_text=str(item.get("question_text", "")),
                        source_text=source_text,
                        answer_text=json.dumps(correct_answers, ensure_ascii=False),
                        acceptable_answers=correct_answers,
                        keyword_rules={"required_any": [], "required_all": []},
                        difficulty=str(item.get("difficulty", "medium")),
                        hint_text=item.get("hint_text"),
                        explanation_text=item.get("explanation_text"),
                        choice_options=options,
                    )

            p = repo.get_problem(problem_id)
            if p:
                result_problems.append(p)
        except Exception as exc:
            print(f"[ProblemSave] 저장 실패: {exc}")

    return result_problems


class QuizWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("퀴즈 풀기")
        self.win.geometry("760x460")
        self.win.minsize(560, 360)

        self.settings = load_settings()
        self.quiz_items: List[Dict[str, Any]] = []
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        self.session = None
        self.record_manager = SolverRecordManager()

        self._radio_var: Optional[tk.StringVar] = None
        self._check_vars: List[tk.BooleanVar] = []
        self._choice_widgets: List[tk.Widget] = []

        self.problem_mode = tk.StringVar(value="subjective")

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
            mode_frame, text="🔄 문제 새로고침",
            command=self._regenerate,
            bg="#2d6cdf", fg="white",
            activebackground="#c98700",
            relief="flat", cursor="hand2",
        ).pack(side="right")

        q_box = tk.LabelFrame(self.win, text="문제", padx=10, pady=10)
        q_box.pack(fill="x", padx=12, pady=(0, 8))
        self.question_var = tk.StringVar()
        tk.Label(
            q_box, textvariable=self.question_var,
            justify="left", wraplength=700,
        ).pack(anchor="w")

        self.answer_frame = tk.LabelFrame(self.win, text="답안 입력", padx=10, pady=10)
        self.answer_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.answer_var = tk.StringVar()
        self.answer_entry = tk.Entry(
            self.answer_frame, textvariable=self.answer_var,
            font=("Segoe UI", 11),
        )
        self.answer_entry.pack(fill="x")

        self.choices_frame = tk.Frame(self.answer_frame)

        btns = tk.Frame(self.win, padx=12, pady=8)
        btns.pack(fill="x")
        tk.Button(
            btns, text="정답 체크", width=12,
            command=self.check_answer,
            bg="#2d6cdf", fg="white",
            activebackground="#2559b7", activeforeground="white",
            relief="flat", cursor="hand2",
        ).pack(side="right")
        tk.Button(
            btns, text="다음 문제", width=12,
            command=self.next_question,
            bg="#e2e2e2", relief="flat", cursor="hand2",
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

    def _set_result(self, text: str) -> None:
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", text)
        self.result_text.config(state="disabled")
        self.result_text.yview_moveto(0)

    def _on_mode_change(self) -> None:
        self._render_question()

    def _load_and_render(self) -> None:
        self.quiz_items = self._load_quiz_items()
        if self.quiz_items:
            first_ocr_id = self.quiz_items[0].get("ocr_result_id")
            self.session = self.record_manager.start_session(
                first_ocr_id, len(self.quiz_items)
            )
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        self._render_question()

    def _load_quiz_items(self) -> List[Dict[str, Any]]:
        loader = ProblemLoader()
        quiz_items: List[Dict[str, Any]] = []
        for row in db.list_ocr_results(limit=20):
            ocr_result_id = row["id"]
            problems = loader.list_for_ocr_result(ocr_result_id)
            if not problems:
                loader.generate_and_store(ocr_result_id)
                problems = loader.list_for_ocr_result(ocr_result_id)
            quiz_items.extend(problems)
        return quiz_items

    def _regenerate(self) -> None:
        api_key = (self.settings.gemini_api_key or "").strip()
        if not api_key:
            messagebox.showwarning(
                "API 키 없음",
                "Gemini API 키가 설정되어 있지 않습니다.\n설정에서 API 키를 입력해 주세요.",
            )
            return

        self.status_label.config(text="⏳ Gemini로 문제를 생성 중입니다...")
        self.win.update_idletasks()

        mode = self.problem_mode.get()

        def _worker():
            new_items: List[Dict[str, Any]] = []
            error_msg: Optional[str] = None
            rows = db.list_ocr_results(limit=20)
            if rows:
                try:
                    items = generate_problems_with_gemini(rows[0]["id"], mode, api_key)
                    new_items.extend(items)
                except Exception as exc:
                    error_msg = str(exc)
            self.win.after(0, lambda: self._on_regenerate_done(new_items, error_msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_regenerate_done(self, new_items: List[Dict[str, Any]], error_msg: Optional[str] = None) -> None:
        self.status_label.config(text="")
        if error_msg or not new_items:
            detail = f"\n\n오류 내용:\n{error_msg}" if error_msg else ""
            messagebox.showerror("오류", f"Gemini로 문제를 생성하지 못했습니다.{detail}")
            return

        self.quiz_items = new_items
        first_ocr_id = self.quiz_items[0].get("ocr_result_id")
        self.session = self.record_manager.start_session(
            first_ocr_id, len(self.quiz_items)
        )
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        self._render_question()

    def _render_question(self) -> None:
        self._set_result("대기 중")
        if not self.quiz_items:
            self.question_var.set("출제할 퀴즈가 없습니다.\n먼저 퀴즈를 생성해 주세요.")
            self.progress_label.config(text="0 / 0")
            return

        q = self.quiz_items[self.current_index]
        self.question_var.set(q.get("question_text", "질문을 불러올 수 없습니다."))
        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.quiz_items)} | 정답 {self.correct_count}/{self.solved_count}"
        )
        self._render_answer_area()

    def _is_objective_mode(self) -> bool:
        return self.problem_mode.get() == "objective"

    def _current_ptype(self) -> str:
        if not self.quiz_items:
            return ""
        return self.quiz_items[self.current_index].get("problem_type", "")

    def _render_answer_area(self) -> None:
        if not self.quiz_items:
            return

        q = self.quiz_items[self.current_index]
        ptype = q.get("problem_type", "")
        mode_is_obj = self._is_objective_mode()
        stored_is_obj = ptype in ("objective_single", "objective_multi")

        if mode_is_obj:
            if ptype == "fill_blank":
                self.choices_frame.pack_forget()
                self._clear_choice_widgets()
                self.answer_entry.pack(fill="x")
                self.answer_var.set("")
                self.answer_entry.focus_set()
            elif not stored_is_obj:
                self.answer_entry.pack_forget()
                self._clear_choice_widgets()
                lbl = tk.Label(
                    self.choices_frame,
                    text="객관식 문제가 없습니다.\n'문제 새로고침'를 눌러 객관식 문제를 생성해 주세요.",
                    fg="#c0392b", justify="left",
                )
                lbl.pack(anchor="w")
                self._choice_widgets.append(lbl)
                self.choices_frame.pack(fill="x")
            else:
                self.answer_entry.pack_forget()
                self._build_choice_widgets(q, ptype)
                self.choices_frame.pack(fill="x")
        else:
            self.choices_frame.pack_forget()
            self._clear_choice_widgets()
            self.answer_entry.pack(fill="x")
            self.answer_var.set("")
            self.answer_entry.focus_set()

    def _clear_choice_widgets(self) -> None:
        for w in self._choice_widgets:
            w.destroy()
        self._choice_widgets.clear()
        self._check_vars.clear()
        self._radio_var = None

    def _build_choice_widgets(self, q: Dict[str, Any], ptype: str) -> None:
        self._clear_choice_widgets()
        options: List[str] = list(q.get("choice_options") or [])
        if not options:
            return

        if ptype == "objective_single":
            self._radio_var = tk.StringVar(value="")
            for opt in options:
                rb = tk.Radiobutton(
                    self.choices_frame,
                    text=opt,
                    variable=self._radio_var,
                    value=opt,
                    anchor="w",
                    justify="left",
                    wraplength=650,
                )
                rb.pack(anchor="w", pady=1)
                self._choice_widgets.append(rb)
        else:
            hint = tk.Label(
                self.choices_frame,
                text="※ 해당하는 답을 모두 선택하세요",
                fg="#888888", font=("Segoe UI", 9),
            )
            hint.pack(anchor="w")
            self._choice_widgets.append(hint)
            for opt in options:
                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(
                    self.choices_frame,
                    text=opt,
                    variable=var,
                    anchor="w",
                    justify="left",
                    wraplength=650,
                )
                cb.pack(anchor="w", pady=1)
                self._check_vars.append(var)
                self._choice_widgets.append(cb)

    def check_answer(self) -> None:
        if not self.quiz_items:
            return

        current_problem = self.quiz_items[self.current_index]
        ptype = current_problem.get("problem_type", "")
        mode_is_obj = self._is_objective_mode()
        stored_is_obj = ptype in ("objective_single", "objective_multi")

        if mode_is_obj and not stored_is_obj and ptype != "fill_blank":
            messagebox.showinfo("알림", "객관식 문제가 없습니다.\n'문제 다시 만들기'를 눌러 먼저 객관식 문제를 생성해 주세요.")
            return

        if mode_is_obj and ptype != "fill_blank":
            user_answer = self._get_objective_answer(ptype, current_problem)
        else:
            user_answer = self.answer_var.get().strip()

        if not user_answer:
            messagebox.showwarning("알림", "답안을 선택/입력해 주세요.")
            return

        if self.session is None:
            messagebox.showerror("오류", "풀이 세션을 시작할 수 없습니다.")
            return

        if mode_is_obj and ptype != "fill_blank":
            self._check_objective(current_problem, ptype, user_answer)
        else:
            self._check_subjective(current_problem, user_answer)

        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.quiz_items)} | 정답 {self.correct_count}/{self.solved_count}"
        )

    def _get_objective_answer(self, ptype: str, problem: Dict[str, Any]) -> str:
        options: List[str] = list(problem.get("choice_options") or [])
        if ptype == "objective_single":
            return self._radio_var.get() if self._radio_var else ""
        else:
            selected = [
                options[i]
                for i, var in enumerate(self._check_vars)
                if var.get()
            ]
            return json.dumps(selected, ensure_ascii=False) if selected else ""

    def _check_objective(
        self,
        problem: Dict[str, Any],
        ptype: str,
        user_answer_raw: str,
    ) -> None:
        correct_answers: List[str] = list(problem.get("acceptable_answers") or [])
        explanation = problem.get("explanation_text") or ""

        if ptype == "objective_single":
            is_correct = user_answer_raw in correct_answers
            self.solved_count += 1
            if is_correct:
                self.correct_count += 1
                self._set_result("✅ 정답입니다!")
            else:
                expl_text = f"\n\n📖 해설: {explanation}" if explanation else ""
                self._set_result(f"❌ 오답입니다.\n정답: {', '.join(correct_answers)}{expl_text}")
        else:
            try:
                user_selected: List[str] = json.loads(user_answer_raw)
            except Exception:
                user_selected = [user_answer_raw]

            correct_set = set(correct_answers)
            user_set = set(user_selected)
            is_correct = correct_set == user_set
            self.solved_count += 1
            if is_correct:
                self.correct_count += 1
                self._set_result("✅ 정답입니다! (모든 정답 선택)")
            else:
                expl_text = f"\n\n📖 해설: {explanation}" if explanation else ""
                self._set_result(f"❌ 오답입니다.\n정답: {', '.join(correct_answers)}{expl_text}")

    def _check_subjective(self, current_problem: Dict[str, Any], user_answer: str) -> None:
        expected = current_problem.get("answer_text", "").strip()
        explanation = current_problem.get("explanation_text") or ""

        gemini_fallback = grade_with_optional_gemini if self.settings.gemini_enabled else None
        record = self.record_manager.submit_answer(
            self.session.id,
            int(current_problem["id"]),
            user_answer,
            gemini_fallback=gemini_fallback,
        )
        self.solved_count += 1
        source = "Gemini 검토" if record.judged_by == "gemini" else "기본 채점"
        expl_text = f"\n\n📖 해설: {explanation}" if (explanation and record.final_status != "correct") else ""

        if record.final_status == "correct":
            self.correct_count += 1
            self._set_result(f"✅ 정답입니다. 점수: {record.final_score}\n판정: {source}")
        elif record.final_status == "ambiguous":
            feedback_text = f"\n피드백: {record.feedback}" if record.feedback else ""
            self._set_result(
                f"🔶 애매한 답변입니다. 점수: {record.final_score}\n"
                f"판정: {source}{feedback_text}\n정답 예시: {expected}{expl_text}"
            )
        else:
            feedback_text = f"\n피드백: {record.feedback}" if record.feedback else ""
            self._set_result(
                f"❌ 오답입니다. 점수: {record.final_score}\n"
                f"판정: {source}{feedback_text}\n정답: {expected}{expl_text}"
            )

    def next_question(self) -> None:
        if not self.quiz_items:
            return
        self.current_index = (self.current_index + 1) % len(self.quiz_items)
        self._render_question()


def open_quiz_window(parent: tk.Misc) -> QuizWindow:
    return QuizWindow(parent)
