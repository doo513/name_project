import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..db import get_ocr_result
from .study_repository import StudyRepository


@dataclass
class Problem:
    id: Optional[int]
    ocr_result_id: int
    problem_type: str
    question_text: str
    source_text: str
    answer_text: str
    acceptable_answers: List[str] = field(default_factory=list)
    keyword_rules: Dict[str, Any] = field(default_factory=dict)
    difficulty: str = "medium"
    hint_text: Optional[str] = None
    explanation_text: Optional[str] = None
    choice_options: Optional[List[str]] = None


class ProblemLoader:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.repository = StudyRepository(db_path)

    def generate_and_store(self, ocr_result_id: int) -> List[int]:
        problem_ids: List[int] = []
        for problem in self.build_problems(ocr_result_id):
            problem_id = self.repository.create_problem(
                ocr_result_id=problem.ocr_result_id,
                problem_type=problem.problem_type,
                question_text=problem.question_text,
                source_text=problem.source_text,
                answer_text=problem.answer_text,
                acceptable_answers=problem.acceptable_answers or [problem.answer_text],
                keyword_rules=problem.keyword_rules,
                difficulty=problem.difficulty,
                hint_text=problem.hint_text,
                explanation_text=problem.explanation_text,
                choice_options=problem.choice_options,
            )
            problem_ids.append(problem_id)
        return problem_ids

    def build_problems(self, ocr_result_id: int) -> List[Problem]:
        row = get_ocr_result(ocr_result_id)
        if not row:
            return []
        source_text = (row.get("content") or "").strip()
        translation_text = (row.get("translation_text") or "").strip()
        if not source_text:
            return []
        problems: List[Problem] = []
        translation_problem = self._build_translation_problem(ocr_result_id, source_text, translation_text)
        if translation_problem is not None:
            problems.append(translation_problem)
        problems.extend(self._build_fill_blank_problems(ocr_result_id, source_text))
        return problems

    def list_for_ocr_result(self, ocr_result_id: int) -> List[Dict[str, Any]]:
        return self.repository.list_problems_for_ocr_result(ocr_result_id)

    def _build_translation_problem(
        self,
        ocr_result_id: int,
        source_text: str,
        translation_text: str,
    ) -> Optional[Problem]:
        if not translation_text:
            return None
        return Problem(
            id=None,
            ocr_result_id=ocr_result_id,
            problem_type="sentence_translation",
            question_text=source_text,
            source_text=source_text,
            answer_text=translation_text,
            acceptable_answers=[translation_text],
            keyword_rules={"required_any": [], "required_all": []},
            difficulty="medium",
            hint_text=None,
            explanation_text=translation_text,
            choice_options=None,
        )

    def _build_fill_blank_problems(self, ocr_result_id: int, source_text: str) -> List[Problem]:
        tokens = [token for token in self._tokenize(source_text) if len(token) > 2]
        if not tokens:
            return []
        unique_tokens: List[str] = []
        seen = set()
        for token in tokens:
            normalized = token.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_tokens.append(token)
        selected = unique_tokens[:3]
        problems: List[Problem] = []
        for answer in selected:
            question_text = self._blank_first_occurrence(source_text, answer)
            problems.append(
                Problem(
                    id=None,
                    ocr_result_id=ocr_result_id,
                    problem_type="fill_blank_word",
                    question_text=question_text,
                    source_text=source_text,
                    answer_text=answer,
                    acceptable_answers=[answer],
                    keyword_rules={"required_any": [], "required_all": []},
                    difficulty="easy" if len(answer) <= 5 else "medium",
                    hint_text=f"{len(answer)} letters",
                    explanation_text=answer,
                    choice_options=None,
                )
            )
        return problems

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.split(r"\s+", re.sub(r"[^\w\s]", " ", text)) if token]

    def _blank_first_occurrence(self, text: str, answer: str) -> str:
        pattern = re.compile(rf"\b{re.escape(answer)}\b", re.IGNORECASE)
        return pattern.sub("____", text, count=1)
