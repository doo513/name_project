from dataclasses import dataclass
from typing import Callable, Optional

from .answer_criteria import AnswerEvaluator, DirectGradeResult
from .study_repository import StudyRepository


GeminiFallback = Callable[[str, dict, DirectGradeResult], DirectGradeResult]


@dataclass
class AttemptSession:
    id: int
    ocr_result_id: Optional[int]
    total_problems: int


@dataclass
class AttemptRecord:
    id: int
    session_id: int
    problem_id: int
    final_status: str
    final_score: int
    judged_by: str
    feedback: Optional[str] = None


class SolverRecordManager:
    def __init__(self, repository: Optional[StudyRepository] = None, evaluator: Optional[AnswerEvaluator] = None) -> None:
        self.repository = repository or StudyRepository()
        self.evaluator = evaluator or AnswerEvaluator()

    def start_session(self, ocr_result_id: Optional[int], total_problems: int) -> AttemptSession:
        session_id = self.repository.start_attempt_session(ocr_result_id, total_problems)
        return AttemptSession(session_id, ocr_result_id, total_problems)

    def submit_answer(
        self,
        session_id: int,
        problem_id: int,
        user_answer: str,
        gemini_fallback: Optional[GeminiFallback] = None,
    ) -> AttemptRecord:
        problem = self.repository.get_problem(problem_id)
        if not problem:
            raise ValueError(f"problem not found: {problem_id}")

        direct_result = self.evaluator.grade(user_answer, self.evaluator.from_problem(problem))
        final_result = direct_result
        judged_by = "direct"
        gemini_used = False

        if direct_result.is_ambiguous and gemini_fallback is not None:
            final_result = gemini_fallback(user_answer, problem, direct_result)
            if final_result.reviewed_by_gemini:
                judged_by = "gemini"
                gemini_used = True

        record_id = self.repository.record_attempt(
            session_id=session_id,
            problem_id=problem_id,
            user_answer=user_answer,
            normalized_answer=direct_result.normalized_answer,
            direct_status=direct_result.status,
            direct_score=direct_result.score,
            ambiguity_reason=direct_result.ambiguity_reason,
            gemini_used=gemini_used,
            gemini_feedback=final_result.ambiguity_reason,
            gemini_confidence=final_result.score if gemini_used else None,
            final_status=final_result.status,
            final_score=final_result.score,
            judged_by=judged_by,
        )
        return AttemptRecord(
            record_id,
            session_id,
            problem_id,
            final_result.status,
            final_result.score,
            judged_by,
            final_result.ambiguity_reason,
        )

    def finish_session(self, session_id: int) -> None:
        self.repository.finish_attempt_session(session_id)
