import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai is not installed")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv is not installed; .env 파일을 자동으로 로드하지 않습니다.")


class QuestionGenerator:
    """Gemini 2.5 Flash Lite API를 사용하여 객관식 4지선다형 문제와 정답을 생성합니다."""

    def __init__(self) -> None:
        if DOTENV_AVAILABLE:
            self._load_dotenv()

        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-2.5-flash-lite"
        self.initialized = False

        if not GENAI_AVAILABLE:
            logger.error("❌ google-generativeai package is not installed")
            return

        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY environment variable is not set")
            logger.info("해결책: 프로젝트 루트의 .env 파일에 GEMINI_API_KEY를 설정하세요")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.initialized = True
            logger.info("✓ Gemini API initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini API: {e}")

    def is_available(self) -> bool:
        """API가 사용 가능한지 확인합니다."""
        available = self.initialized and GENAI_AVAILABLE
        if not available:
            if not GENAI_AVAILABLE:
                logger.error("❌ google-generativeai package not available")
            elif not self.api_key:
                logger.error("❌ GEMINI_API_KEY not configured")
            else:
                logger.error("❌ Gemini API initialization failed")
        return available

    def _load_dotenv(self) -> None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logger.info(f"Loaded .env from {env_path}")
            return

        # fallback: search from current working directory upward
        try:
            from dotenv import find_dotenv

            found = find_dotenv(usecwd=True)
            if found:
                load_dotenv(found, override=False)
                logger.info(f"Loaded .env from {found}")
                return
        except Exception:
            pass

        logger.info("No .env file found for Gemini API key loading")

    def generate_questions(
        self,
        ocr_contents: List[str],
        language: str = "ko",
        num_questions: int = 5,
        mode: str = "objective",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        OCR 결과 콘텐츠로부터 문제를 생성합니다.

        Args:
            ocr_contents: OCR로 추출한 텍스트 목록
            language: 문제 생성 언어 (기본값: "ko")
            num_questions: 생성할 문제 개수 (기본값: 5)
            mode: "objective" 또는 "subjective"

        Returns:
            문제 딕셔너리 리스트
        """
        if not self.is_available():
            logger.error("❌ Gemini API is not available")
            return None

        if not ocr_contents or not any(c.strip() for c in ocr_contents):
            logger.warning("⚠️ No valid OCR content provided")
            return None

        valid_contents = [c.strip() for c in ocr_contents if c.strip()]
        logger.info(f"📚 Loaded {len(valid_contents)} study materials")

        prompt = self._build_prompt(valid_contents, language, num_questions, mode)
        logger.debug(f"Prompt: {prompt[:100]}...")

        try:
            logger.info(f"🔄 Calling Gemini API (model: {self.model_name})...")
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            if not response or not response.text:
                logger.error("❌ Empty response from Gemini API")
                return None

            logger.info(f"✓ Received response from Gemini API")
            logger.debug(f"Response: {response.text[:200]}...")

            questions = self._parse_response(response.text)
            
            if questions:
                logger.info(f"✓ Generated {len(questions)} questions successfully")
                return questions
            else:
                logger.error("❌ Failed to parse questions from response")
                return None

        except Exception as e:
            logger.error(f"❌ Error generating questions: {e}", exc_info=True)
            return None

    def _build_prompt(self, contents: List[str], language: str, num_questions: int, mode: str) -> str:
        """프롬프트를 빌드합니다."""
        contents_text = "\n---\n".join(contents[:5])
        mode_text = "객관식" if mode == "objective" else "주관식"
        style_text = (
            "언어 학습 스타일로, 어휘와 독해를 돕는 문제를 만들어줘. "
            "정답이 명확하면서도 문장의 의미를 이해할 수 있도록 작성해줘."
        )

        if language == "ko":
            if mode == "objective":
                prompt = f"""다음 텍스트를 기반으로 {num_questions}개의 객관식 문제를 만들어줘.

텍스트:
{contents_text}

문제 유형: 언어 학습 형식, 한국어로 작성
스타일: {style_text}

JSON으로만 응답해줘:
[{{"question": "문제", "options": ["선택지1", "선택지2", "선택지3", "선택지4"], "answer": "정답"}}]

필수: 정답은 options 중 정확히 하나"""
            else:
                prompt = f"""다음 텍스트를 기반으로 {num_questions}개의 주관식 문제를 만들어줘.

텍스트:
{contents_text}

문제 유형: 언어 학습 형식, 한국어로 작성
스타일: {style_text}

JSON으로만 응답해줘:
[{{"question": "문제", "answer": "정답"}}]"""
        else:
            if mode == "objective":
                prompt = f"""Create exactly {num_questions} multiple-choice questions based on the given texts.

Texts:
{contents_text}

Question style: language learning, vocabulary and comprehension focused.
Important: answer must be one of the options.

Respond only as JSON array:
[
  {{"question": "Question text", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "answer": "Correct answer"}}
]"""
            else:
                prompt = f"""Create exactly {num_questions} short-answer questions based on the given texts.

Texts:
{contents_text}

Question style: language learning, vocabulary and comprehension focused.

Respond only as JSON array:
[
  {{"question": "Question text", "answer": "Correct answer"}}
]"""

        return prompt

    def _parse_response(self, response_text: str) -> Optional[List[Dict[str, Any]]]:
        """API 응답을 파싱하여 객관식 문제를 추출합니다."""
        try:
            logger.debug(f"Parsing response: {response_text[:200]}...")
            
            # JSON 추출 시도
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1

            if json_start == -1 or json_end == 0:
                logger.error("No JSON array found in response")
                logger.error(f"Full response: {response_text}")
                return None

            json_str = response_text[json_start:json_end]
            logger.debug(f"Extracted JSON: {json_str[:200]}...")
            
            parsed = json.loads(json_str)
            
            if not isinstance(parsed, list):
                logger.error(f"Response is not a JSON array: {type(parsed)}")
                return None

            questions = []
            for idx, item in enumerate(parsed):
                try:
                    if not isinstance(item, dict):
                        logger.warning(f"Item {idx} is not a dict: {type(item)}")
                        continue
                        
                    question = item.get("question", "").strip()
                    options = item.get("options", [])
                    answer = item.get("answer", "").strip()

                    if not question:
                        logger.warning(f"Item {idx}: missing question")
                        continue
                    
                    if not answer:
                        logger.warning(f"Item {idx}: missing answer")
                        continue

                    if options is None:
                        options = []
                    if not isinstance(options, list):
                        logger.warning(f"Item {idx}: options is not a list: {type(options)}")
                        continue

                    options = [str(opt).strip() for opt in options if str(opt).strip()]
                    if options and len(options) != 4:
                        logger.warning(f"Item {idx}: expected 4 options, got {len(options)}")
                        continue

                    if options and answer not in options:
                        logger.warning(f"Item {idx}: answer '{answer}' not in options: {options}")
                        continue

                    question_data = {
                        "question": question,
                        "answer": answer,
                        "meta": f"Generated #{idx + 1}",
                    }
                    if options:
                        question_data["options"] = options

                    questions.append(question_data)
                    logger.debug(f"Successfully parsed question {idx}: {question[:50]}...")

                except Exception as e:
                    logger.error(f"Error parsing item {idx}: {e}")
                    logger.debug(f"Item content: {item}")
                    continue

            if not questions:
                logger.error(f"No valid questions parsed from {len(parsed)} items")
                return None

            logger.info(f"✓ Successfully parsed {len(questions)} questions")
            return questions

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return None

    @staticmethod
    def create_prompt_from_ocr_data(ocr_data: Dict[str, Any]) -> str:
        """OCR 데이터로부터 프롬프트를 생성합니다."""
        content = ocr_data.get("content", "")
        translation = ocr_data.get("translation", "")
        timestamp = ocr_data.get("time", "")

        prompt_parts = []
        if content:
            prompt_parts.append(f"원문: {content}")
        if translation:
            prompt_parts.append(f"번역: {translation}")

        return "\n".join(prompt_parts) if prompt_parts else ""
