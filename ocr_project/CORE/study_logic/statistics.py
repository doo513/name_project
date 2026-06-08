from typing import Any, Dict, Optional

from .study_repository import StudyRepository


class StudyStatistics:
    def __init__(self, repository: Optional[StudyRepository] = None) -> None:
        self.repository = repository or StudyRepository()

    def session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self.repository.get_session_summary(session_id)

    def session_records(self, session_id: int):
        return self.repository.list_attempt_records(session_id)
