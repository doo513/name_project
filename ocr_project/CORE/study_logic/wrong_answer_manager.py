from typing import Any, Dict, List, Optional

from .study_repository import StudyRepository


class WrongAnswerManager:
    def __init__(self, repository: Optional[StudyRepository] = None) -> None:
        self.repository = repository or StudyRepository()

    def list_unresolved(self) -> List[Dict[str, Any]]:
        return self.repository.list_wrong_answers(unresolved_only=True)

    def list_all(self) -> List[Dict[str, Any]]:
        return self.repository.list_wrong_answers(unresolved_only=False)

    def resolve(self, problem_id: int) -> None:
        self.repository.resolve_wrong_answer(problem_id)
