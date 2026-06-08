import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional


@dataclass(frozen=True)
class StabilizerConfig:
    required_matches: int = 2
    similarity_threshold: float = 0.92


@dataclass(frozen=True)
class StabilizerDecision:
    candidate_text: Optional[str]
    candidate_normalized: Optional[str]
    candidate_match_count: int
    should_start_hold: bool
    should_cancel_hold: bool
    status: Optional[str]


@dataclass(frozen=True)
class ConfirmedCandidate:
    text: str
    languages: List[str]


class OCRStabilizer:
    def __init__(self, config: Optional[StabilizerConfig] = None) -> None:
        self.config = config or StabilizerConfig()
        self.candidate_text: Optional[str] = None
        self.candidate_normalized: Optional[str] = None
        self.candidate_match_count = 0
        self.candidate_languages: List[str] = []
        self.hold_expected_normalized: Optional[str] = None

    def submit(self, lines: List[str], languages: List[str]) -> StabilizerDecision:
        candidate_text = "\n".join(line.strip() for line in lines if line and line.strip()).strip()
        normalized = self.normalize(candidate_text)
        if not normalized:
            self.reset()
            return StabilizerDecision(None, None, 0, False, True, None)

        should_cancel_hold = False
        if self._is_similar_to_current_candidate(normalized):
            self.candidate_match_count += 1
            if self._prefer_candidate_text(candidate_text):
                previous_normalized = self.candidate_normalized
                self.candidate_text = candidate_text
                self.candidate_normalized = normalized
                should_cancel_hold = previous_normalized != normalized and self.hold_expected_normalized is not None
                if should_cancel_hold:
                    self.hold_expected_normalized = None
            self.candidate_languages = list(languages)
        else:
            self.reset()
            self.candidate_text = candidate_text
            self.candidate_normalized = normalized
            self.candidate_match_count = 1
            self.candidate_languages = list(languages)
            should_cancel_hold = True

        should_start_hold = False
        if self.candidate_match_count >= self.config.required_matches:
            should_start_hold = self.hold_expected_normalized is None
            status = f"Candidate matched {self.candidate_match_count} time(s). Confirming after hold..."
        else:
            status = (
                "Candidate detected. Waiting for another similar OCR result "
                f"({self.candidate_match_count}/{self.config.required_matches})."
            )

        return StabilizerDecision(
            candidate_text=self.candidate_text,
            candidate_normalized=self.candidate_normalized,
            candidate_match_count=self.candidate_match_count,
            should_start_hold=should_start_hold,
            should_cancel_hold=should_cancel_hold,
            status=status,
        )

    def start_hold(self) -> Optional[str]:
        self.hold_expected_normalized = self.candidate_normalized
        return self.hold_expected_normalized

    def confirm_if_stable(self, expected_normalized: str) -> Optional[ConfirmedCandidate]:
        self.hold_expected_normalized = None
        if not self.candidate_text or not self.candidate_normalized:
            return None
        if self.candidate_normalized != expected_normalized:
            return None
        if self.candidate_match_count < self.config.required_matches:
            return None

        confirmed_text = self.candidate_text.strip()
        if not confirmed_text:
            return None

        confirmed = ConfirmedCandidate(text=confirmed_text, languages=list(self.candidate_languages))
        self.reset()
        return confirmed

    def reset(self) -> None:
        self.candidate_text = None
        self.candidate_normalized = None
        self.candidate_match_count = 0
        self.candidate_languages = []
        self.hold_expected_normalized = None

    def needs_sample(self) -> bool:
        return self.candidate_text is not None and self.candidate_match_count < self.config.required_matches

    def normalize(self, text: str) -> str:
        lowered = text.casefold().strip()
        collapsed = re.sub(r"\s+", " ", lowered)
        return re.sub(r"[^\w\s가-힣ぁ-ゟ゠-ヿ一-龯]", "", collapsed).strip()

    def _is_similar_to_current_candidate(self, normalized: str) -> bool:
        if not self.candidate_normalized:
            return False
        if normalized == self.candidate_normalized:
            return True
        similarity = SequenceMatcher(None, self.candidate_normalized, normalized).ratio()
        return similarity >= self.config.similarity_threshold

    def _prefer_candidate_text(self, new_text: str) -> bool:
        if not self.candidate_text:
            return True
        return len(new_text.strip()) >= len(self.candidate_text.strip())
