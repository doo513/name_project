import random
import tkinter as tk
from tkinter import messagebox
import threading
import logging
import json

from CORE import db
from CORE.question_generator import QuestionGenerator

logger = logging.getLogger(__name__)


class TestWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("테스트 UI")
        self.win.geometry("760x460")
        self.win.minsize(560, 360)

        self.questions = []
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        self.is_loading = True

        self._build_ui()
        
        # 별도 스레드에서 문제 로드
        load_thread = threading.Thread(target=self._load_questions_async, daemon=True)
        load_thread.start()

    def _build_ui(self) -> None:
        top = tk.Frame(self.win, padx=12, pady=10)
        top.pack(fill="x")
        self.title_label = tk.Label(top, text="언어 학습 문제", font=("Segoe UI", 12, "bold"))
        self.title_label.pack(side="left")
        self.progress_label = tk.Label(top, text="", fg="#555555")
        self.progress_label.pack(side="right")

        control_frame = tk.Frame(self.win, padx=12, pady=6)
        control_frame.pack(fill="x")
        tk.Label(control_frame, text="문제 유형:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.question_mode_var = tk.StringVar(value="objective")
        tk.OptionMenu(
            control_frame,
            self.question_mode_var,
            "objective",
            "subjective",
            command=self._on_mode_change,
        ).pack(side="left", padx=(4, 8))
        tk.Button(
            control_frame,
            text="문제 새로고침",
            command=self.reload_questions,
            bg="#5E66F2",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=12,
        ).pack(side="right")

        q_box = tk.LabelFrame(self.win, text="문제", padx=10, pady=10)
        q_box.pack(fill="x", padx=12, pady=(0, 8))
        self.question_var = tk.StringVar()
        tk.Label(q_box, textvariable=self.question_var, justify="left", wraplength=700).pack(anchor="w")

        # 답안 프레임
        a_box = tk.LabelFrame(self.win, text="답안", padx=10, pady=10)
        a_box.pack(fill="both", padx=12, pady=(0, 8), expand=True)
        
        self.option_frame = tk.Frame(a_box)
        self.option_frame.pack(fill="both", expand=True)
        self.selected_option = tk.StringVar()
        self.option_buttons = []
        
        for i in range(4):
            btn = tk.Radiobutton(
                self.option_frame,
                text="",
                variable=self.selected_option,
                value=f"option_{i}",
                font=("Segoe UI", 10),
                anchor="w",
                justify="left",
                wraplength=650
            )
            btn.pack(fill="x", pady=5, anchor="w")
            self.option_buttons.append(btn)

        self.subjective_frame = tk.Frame(a_box)
        self.subjective_frame.pack(fill="x")
        self.answer_var = tk.StringVar()
        self.answer_entry = tk.Entry(self.subjective_frame, textvariable=self.answer_var, font=("Segoe UI", 11))
        self.answer_entry.pack(fill="x")
        self.subjective_frame.pack_forget()

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
        
        # 초기 로딩 표시
        self.question_var.set("⏳ Gemini API로 문제를 생성하는 중...\n\n잠시만 기다려주세요.\n(인터넷 연결 확인 필수)")
        self.progress_label.config(text="로드 중...")

    def _load_questions_async(self) -> None:
        """별도 스레드에서 Gemini API로 문제를 비동기로 로드합니다."""
        try:
            # DB에서 OCR 결과 로드 (payload_json 포함)
            rows = db.list_ocr_results(limit=100)
            
            if not rows:
                logger.warning("No data found in database")
                self.win.after(0, lambda: messagebox.showwarning("알림", "DB에 저장된 데이터가 없습니다.\n먼저 OCR 결과를 저장해주세요."))
                self.questions = []
                self.win.after(0, self._render_question)
                return
            
            # 저장된 데이터 추출 (원문 + 번역)
            study_materials = []
            for row in rows:
                payload_json = row.get("payload_json")
                if payload_json:
                    try:
                        payload = json.loads(payload_json)
                        content = payload.get("content", "").strip()
                        translation = payload.get("translation", "").strip()
                        
                        material = content
                        if translation:
                            material = f"[원문]\n{content}\n\n[번역]\n{translation}"
                        
                        if material:
                            study_materials.append(material)
                    except Exception as e:
                        logger.error(f"Error parsing payload_json: {e}")
                        content = row.get("content", "").strip()
                        if content:
                            study_materials.append(content)
                else:
                    # payload_json이 없으면 content만 사용
                    content = row.get("content", "").strip()
                    if content:
                        study_materials.append(content)

            if not study_materials:
                logger.warning("No valid study materials found")
                self.win.after(0, lambda: messagebox.showwarning("알림", "유효한 학습 자료가 없습니다."))
                self.questions = []
                self.win.after(0, self._render_question)
                return

            logger.info(f"Loaded {len(study_materials)} study materials from database")

            # Gemini API로 문제 생성
            generator = QuestionGenerator()
            
            if not generator.is_available():
                error_msg = "❌ Gemini API를 사용할 수 없습니다.\n\n설정 확인:\n1. .env 파일에 GEMINI_API_KEY 설정했는지 확인\n2. API 키가 유효한지 확인\n3. 인터넷 연결 확인"
                logger.error(error_msg)
                self.win.after(0, lambda: messagebox.showerror("Gemini API 오류", error_msg))
                self.questions = self._get_fallback_questions()
                self.win.after(0, self._render_question)
                return

            logger.info("Generating questions with Gemini API...")
            generated_questions = generator.generate_questions(
                study_materials,
                language="ko",
                num_questions=min(5, len(study_materials)),
                mode=self.question_mode_var.get(),
            )
            
            if generated_questions:
                self.questions = generated_questions
                random.shuffle(self.questions)
                logger.info(f"✓ Successfully generated {len(self.questions)} questions")
            else:
                error_msg = "⚠️ Gemini API 응답이 유효하지 않습니다.\n문제 생성에 실패했습니다."
                logger.error(error_msg)
                self.win.after(0, lambda: messagebox.showwarning("생성 실패", error_msg))
                self.questions = self._get_fallback_questions()

        except Exception as e:
            error_msg = f"❌ 오류 발생: {str(e)}"
            logger.error(f"Error loading questions: {e}", exc_info=True)
            self.win.after(0, lambda: messagebox.showerror("오류", error_msg))
            self.questions = []
        
        finally:
            self.is_loading = False
            # UI 업데이트는 메인 스레드에서 수행
            self.win.after(0, self._render_question)

    def _get_fallback_questions(self) -> list:
        """Gemini API 사용 불가 시 DB 또는 더미 문제를 반환합니다."""
        questions = [
            {
                "question": "비타민 C의 주요 역할은 무엇인가요?",
                "options": [
                    "항산화 작용, 콜라겐 합성, 면역 체계 강화",
                    "칼슘 흡수 촉진",
                    "철분 대사",
                    "혈액 응고"
                ],
                "answer": "항산화 작용, 콜라겐 합성, 면역 체계 강화",
                "meta": "더미1",
            },
            {
                "question": "다음 중 대사의 정의로 가장 올바른 것은?",
                "options": [
                    "살아있는 유기체 내에서 일어나는 모든 화학 반응",
                    "세포 분열 과정",
                    "호르몬 분비",
                    "신경 신호 전달"
                ],
                "answer": "살아있는 유기체 내에서 일어나는 모든 화학 반응",
                "meta": "더미2",
            },
            {
                "question": "DNA의 주요 기능은 무엇인가요?",
                "options": [
                    "유전 정보의 저장 및 전달",
                    "에너지 생산",
                    "단백질 운송",
                    "세포벽 형성"
                ],
                "answer": "유전 정보의 저장 및 전달",
                "meta": "더미3",
            },
        ]

        random.shuffle(questions)
        return questions

    def _render_question(self) -> None:
        if not self.questions:
            self.question_var.set("❌ 문제를 불러올 수 없습니다.\n\n다음을 확인하세요:\n1. DB에 저장된 데이터 확인\n2. Gemini API 키 설정 확인\n3. 콘솔 로그에서 오류 확인")
            self.progress_label.config(text="0 / 0")
            for btn in self.option_buttons:
                btn.pack_forget()
            self.option_frame.pack_forget()
            self.subjective_frame.pack_forget()
            return

        q = self.questions[self.current_index]
        self.question_var.set(q["question"])

        mode = self.question_mode_var.get()
        if mode == "subjective":
            self.option_frame.pack_forget()
            self.subjective_frame.pack(fill="x")
            self.answer_var.set("")
            self.answer_entry.focus_set()
        else:
            self.subjective_frame.pack_forget()
            self.option_frame.pack(fill="both", expand=True)
            options = q.get("options", [])
            for i, btn in enumerate(self.option_buttons):
                if i < len(options):
                    btn.config(text=options[i])
                    btn.pack(fill="x", pady=5, anchor="w")
                else:
                    btn.pack_forget()
            self.selected_option.set("")
            if self.option_buttons:
                self.option_buttons[0].focus_set()

        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.questions)} | 정답 {self.correct_count}/{self.solved_count}"
        )

    def check_answer(self) -> None:
        if not self.questions:
            messagebox.showwarning("알림", "문제가 아직 로드되지 않았습니다.")
            return

        q = self.questions[self.current_index]
        mode = self.question_mode_var.get()
        expected_answer = q["answer"].strip()
        self.solved_count += 1

        if mode == "subjective":
            user_answer = self.answer_var.get().strip()
            if not user_answer:
                messagebox.showwarning("알림", "답안을 입력해주세요.")
                self.solved_count -= 1
                return

            if user_answer == expected_answer:
                self.correct_count += 1
                self.result_var.set("✓ 정답입니다!")
            else:
                self.result_var.set(f"✗ 오답입니다.\n정답: {expected_answer}")
        else:
            selected_idx_str = self.selected_option.get()
            if not selected_idx_str:
                messagebox.showwarning("알림", "선택지를 선택해주세요.")
                self.solved_count -= 1
                return

            selected_idx = int(selected_idx_str.split("_")[1])
            selected_option_text = q["options"][selected_idx]
            if selected_option_text.strip() == expected_answer:
                self.correct_count += 1
                self.result_var.set("✓ 정답입니다!")
            else:
                self.result_var.set(f"✗ 오답입니다.\n정답: {expected_answer}")

        self.progress_label.config(
            text=f"{self.current_index + 1} / {len(self.questions)} | 정답 {self.correct_count}/{self.solved_count}"
        )

    def _on_mode_change(self, value: str) -> None:
        self.question_mode_var.set(value)
        self._render_question()

    def reload_questions(self) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        self.question_var.set("⏳ 문제를 다시 로드하는 중입니다... 잠시만 기다려주세요.")
        self.progress_label.config(text="로드 중...")
        self.questions = []
        self.current_index = 0
        self.correct_count = 0
        self.solved_count = 0
        threading.Thread(target=self._load_questions_async, daemon=True).start()

    def next_question(self) -> None:
        if not self.questions:
            return
        self.current_index = (self.current_index + 1) % len(self.questions)
        self.result_var.set("대기 중")
        self._render_question()


def open_test_window(parent: tk.Misc) -> TestWindow:
    return TestWindow(parent)
