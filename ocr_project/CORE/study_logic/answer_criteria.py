import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AnswerCriteria:
    problem_id: int
    problem_type: str
    answer_text: str
    acceptable_answers: List[str]
    keyword_rules: Dict[str, List[str]]


@dataclass
class DirectGradeResult:
    status: str
    score: int
    normalized_answer: str
    ambiguity_reason: Optional[str] = None
    reviewed_by_gemini: bool = False

    @property
    def is_ambiguous(self) -> bool:
        return self.status == "ambiguous"


class AnswerEvaluator:
    def normalize(self, text: str) -> str:
        collapsed = " ".join((text or "").strip().casefold().split())
        return re.sub(r"[^\w\s]", "", collapsed)

    def from_problem(self, problem: Dict[str, Any]) -> AnswerCriteria:
        acceptable_answers = list(problem.get("acceptable_answers") or [])
        if not acceptable_answers and problem.get("answer_text"):
            acceptable_answers = [str(problem["answer_text"])]
        return AnswerCriteria(
            problem_id=int(problem["id"]),
            problem_type=str(problem.get("problem_type") or ""),
            answer_text=str(problem.get("answer_text") or ""),
            acceptable_answers=acceptable_answers,
            keyword_rules=dict(problem.get("keyword_rules") or {}),
        )

    def grade(self, user_answer: str, criteria: AnswerCriteria) -> DirectGradeResult:
        normalized_user = self.normalize(user_answer)
        if not normalized_user:
            return DirectGradeResult("incorrect", 0, normalized_user)

        normalized_answers = [self.normalize(answer) for answer in criteria.acceptable_answers]
        if normalized_user in normalized_answers:
            return DirectGradeResult("correct", 100, normalized_user)

        required_all = [self.normalize(word) for word in criteria.keyword_rules.get("required_all", [])]
        required_any = [self.normalize(word) for word in criteria.keyword_rules.get("required_any", [])]

        if required_all and all(word in normalized_user for word in required_all):
            return DirectGradeResult("correct", 100, normalized_user)
        if required_any and any(word in normalized_user for word in required_any):
            return DirectGradeResult("ambiguous", 60, normalized_user, "keyword matched but exact answer did not match")

        best_overlap = self._best_token_overlap(normalized_user, normalized_answers)
        if criteria.problem_type == "sentence_translation" and best_overlap >= 0.6:
            return DirectGradeResult("ambiguous", int(best_overlap * 100), normalized_user, "translation is similar but not exact")
        if best_overlap >= 0.85:
            return DirectGradeResult("ambiguous", int(best_overlap * 100), normalized_user, "answer is very close to an accepted answer")
        return DirectGradeResult("incorrect", 0, normalized_user)

    def _best_token_overlap(self, normalized_user: str, normalized_answers: List[str]) -> float:
        user_tokens = set(normalized_user.split())
        if not user_tokens:
            return 0.0
        best = 0.0
        for answer in normalized_answers:
            answer_tokens = set(answer.split())
            if not answer_tokens:
                continue
            overlap = len(user_tokens & answer_tokens) / max(len(answer_tokens), 1)
            best = max(best, overlap)
        return best
