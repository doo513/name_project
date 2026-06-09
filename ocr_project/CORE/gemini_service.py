import importlib
import json
from typing import Any, Dict, Optional

from .app_settings import load_settings
from .study_logic.answer_criteria import DirectGradeResult


class GeminiService:
    RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = (api_key if api_key is not None else load_settings().gemini_api_key).strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def grade_ambiguous_answer(
        self,
        user_answer: str,
        problem: Dict[str, Any],
        direct_result: DirectGradeResult,
    ) -> DirectGradeResult:
        if not self.api_key:
            return direct_result

        try:
            genai = importlib.import_module("google.genai")
        except Exception:
            return DirectGradeResult(
                direct_result.status,
                direct_result.score,
                direct_result.normalized_answer,
                "Gemini API key is saved, but google-genai is not installed.",
                reviewed_by_gemini=False,
            )

        try:
            client = self._create_client(genai)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=self._build_grading_prompt(user_answer, problem, direct_result),
            )
            return self._parse_response(getattr(response, "text", ""), direct_result)
        except Exception as exc:
            message = self._format_failure_message(exc)
            return DirectGradeResult(
                direct_result.status,
                direct_result.score,
                direct_result.normalized_answer,
                message,
                reviewed_by_gemini=False,
            )

    def test_connection(self) -> str:
        if not self.api_key:
            return "Gemini API 키가 입력되지 않았습니다. Gemini 없이도 기본 채점은 사용할 수 있습니다."

        try:
            genai = importlib.import_module("google.genai")
        except Exception:
            return "google-genai 패키지가 설치되어 있지 않습니다. requirements.txt 설치 후 다시 시도해 주세요."

        try:
            client = self._create_client(genai)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Reply with OK if this Gemini API key can be used.",
            )
            text = (getattr(response, "text", "") or "").strip()
        except Exception as exc:
            if self._is_transient_error(exc):
                return "Gemini가 일시적으로 불안정합니다. 잠시 후 다시 시도해 주세요. API 없이도 기본 채점은 계속 사용할 수 있습니다."
            return "Gemini 연결에 실패했습니다. API 키와 네트워크 상태를 확인해 주세요. API 없이도 기본 채점은 계속 사용할 수 있습니다."

        return f"Gemini 연결 성공: {text or 'OK'}"

    def _create_client(self, genai):
        try:
            types = importlib.import_module("google.genai.types")
            retry_options = types.HttpRetryOptions(
                attempts=3,
                initial_delay=1.0,
                max_delay=8.0,
                http_status_codes=self.RETRY_STATUS_CODES,
            )
            http_options = types.HttpOptions(retry_options=retry_options)
            return genai.Client(api_key=self.api_key, http_options=http_options)
        except Exception:
            return genai.Client(api_key=self.api_key)

    def _format_failure_message(self, exc: Exception) -> str:
        if self._is_transient_error(exc):
            return "Gemini가 일시적으로 응답하지 않아 기본 채점 결과를 사용했습니다. 잠시 후 다시 시도하면 Gemini 검토를 받을 수 있습니다."
        return "Gemini 검토를 완료하지 못해 기본 채점 결과를 사용했습니다. API 키와 네트워크 상태를 확인해 주세요."

    def _is_transient_error(self, exc: Exception) -> bool:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if code in {408, 429, 500, 502, 503, 504}:
            return True

        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "503",
                "unavailable",
                "overloaded",
                "timeout",
                "timed out",
                "connecterror",
                "temporarily",
            )
        )

    def _build_grading_prompt(
        self,
        user_answer: str,
        problem: Dict[str, Any],
        direct_result: DirectGradeResult,
    ) -> str:
        return (
            "You are grading a language-learning quiz answer. "
            "Return only JSON with keys status, score, feedback. "
            "status must be one of correct, incorrect, ambiguous. "
            "score must be an integer from 0 to 100.\n\n"
            f"Question: {problem.get('question_text', '')}\n"
            f"Expected answer: {problem.get('answer_text', '')}\n"
            f"Accepted answers: {problem.get('acceptable_answers', [])}\n"
            f"User answer: {user_answer}\n"
            f"Direct grader status: {direct_result.status}\n"
            f"Direct grader score: {direct_result.score}\n"
            f"Direct grader reason: {direct_result.ambiguity_reason or ''}\n"
        )

    def _parse_response(self, text: str, direct_result: DirectGradeResult) -> DirectGradeResult:
        payload = self._extract_json(text)
        if payload is None:
            return DirectGradeResult(
                direct_result.status,
                direct_result.score,
                direct_result.normalized_answer,
                "Gemini 응답을 해석할 수 없어 기본 채점 결과를 사용했습니다.",
                reviewed_by_gemini=False,
            )

        status = str(payload.get("status") or direct_result.status).strip().lower()
        if status not in {"correct", "incorrect", "ambiguous"}:
            status = direct_result.status

        try:
            score = int(payload.get("score", direct_result.score))
        except (TypeError, ValueError):
            score = direct_result.score
        score = max(0, min(100, score))

        feedback = str(payload.get("feedback") or direct_result.ambiguity_reason or "Gemini reviewed the answer.")
        return DirectGradeResult(status, score, direct_result.normalized_answer, feedback, reviewed_by_gemini=True)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None


def grade_with_optional_gemini(
    user_answer: str,
    problem: Dict[str, Any],
    direct_result: DirectGradeResult,
) -> DirectGradeResult:
    return GeminiService().grade_ambiguous_answer(user_answer, problem, direct_result)
