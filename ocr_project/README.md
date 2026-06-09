# ocr_project

Python `tkinter`로 만든 Desktop OCR 번역/학습 앱입니다. 화면 영역을 선택하고 주기적으로 캡처한 뒤, 이미지 변경이 감지되면 OCR을 수행합니다. OCR 결과가 일정 기준으로 안정화되면 선택한 목표 언어로 번역하고, 사용자가 직접 저장할 수 있습니다.

## 설치 및 실행

프로젝트 루트에서 `uv`로 가상환경을 만들고 의존성을 설치합니다.

```bash
uv venv
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

```bash
uv pip install -r requirements.txt
```

캡처 백엔드 확인:

```bash
uv run python -c "from PIL import ImageGrab; import mss; print('capture backend ok')"
```

실행:

```bash
uv run python ocr_project/main.py
```

## 사용 방법

1. `uv run python ocr_project/main.py` 실행
2. 메인 화면에서 `원본` 언어와 `번역` 언어 선택
3. `OCR 번역 시작` 클릭
4. 마우스로 캡처 영역 드래그
5. `OCR 번역 패널`에서 확정 OCR/번역 결과 확인
6. 영역을 바꾸려면 `레이어 재설정`으로 OCR 영역 재선택
7. 필요하면 `다시 번역` 클릭
8. 확정된 OCR/번역 결과를 확인한 뒤 `저장` 클릭

## 현재 구조

```text
main.py
|- CORE.language_config   # UI/OCR/번역 언어 코드 단일 관리
|- CORE.ocr_engine        # EasyOCR 래핑
|- CORE.ocr_service       # 이미지 OCR 실행 + OCR 텍스트 정리
|- CORE.ocr_stabilizer    # OCR 후보 안정화/확정 로직
|- CORE.translation_service # 번역 서비스
|- CORE.db                # 로컬 데이터베이스 저장 및 조회
|- CORE.study_logic       # 문제 생성/풀이 기록/오답 관리
|- UI.selector            # 영역 선택 오버레이
|- UI.capture_monitor     # 주기적 캡처 패널 및 결과 표시
|- UI.study_list          # 저장된 결과 목록
|- UI.quiz_ui             # 퀴즈 UI
\- UI.settings_ui          # OCR 확정 조건 설정 UI
```

## OCR/번역 흐름

```text
1. 사용자가 원본 언어와 번역 언어 선택
2. OCR 번역 시작
3. 영역 선택
4. CaptureMonitor가 2초마다 화면 캡처
5. 이미지 변경 감지
6. OCRService가 원본 언어 기준으로 OCR 수행
7. OCRStabilizer가 후보 문장을 비교하여 확정
8. TranslationService가 확정 원문을 목표 언어로 번역
9. 사용자가 확인 후 SQLite에 저장
```

## 언어 선택 구조

언어 관련 설정은 다음 파일에서만 관리합니다.

```text
CORE/language_config.py
```

기존처럼 `main.py`와 `capture_monitor.py`에 언어 리스트를 따로 두지 않습니다. UI, OCR, 번역에서 필요한 코드는 `LanguageOption` 하나로 묶어서 관리합니다.

```python
LanguageOption("Korean", "ko", "ko", "ko")
LanguageOption("English", "en", "en", "en")
LanguageOption("Japanese", "ja", "ja", "ja")
LanguageOption("Chinese Simplified", "zh-CN", "ch_sim", "zh-CN")
LanguageOption("Chinese Traditional", "zh-TW", "ch_tra", "zh-TW")
```

### 코드 분리 기준

| 구분 | 역할 |
|---|---|
| UI 코드 | 콤보박스에서 선택하는 공통 코드 |
| OCR 코드 | EasyOCR에 넘기는 코드 |
| 번역 코드 | deep-translator에 넘기는 코드 |

### 예시

| 사용자가 선택한 방향 | OCRService 입력 | TranslationService 입력 |
|---|---|---|
| `en -> ko` | `['en']` | `en -> ko` |
| `ko -> ja` | `['ko']` | `ko -> ja` |
| `ja -> ko` | `['ja']` | `ja -> ko` |
| `zh-CN -> ko` | `['ch_sim']` | `zh-CN -> ko` |
| `zh-TW -> en` | `['ch_tra']` | `zh-TW -> en` |

중요한 점은 OCR에는 번역 대상 언어를 넣지 않는다는 것입니다. OCR은 원본 화면에 있는 글자 언어만 사용하고, 번역 단계에서만 원본/목표 언어를 함께 사용합니다.

## 현재 동작 중인 기능

- 마우스로 영역 선택
- 2초 주기 캡처
- 이미지 변경 감지 후 OCR
- OCR 후보 안정화 후 확정
- 원본 언어 → 번역 언어 선택
- OCR 언어 코드와 번역 언어 코드 분리
- 메인 화면 선택값을 캡처 패널에 전달
- 레이어 재설정 버튼으로 OCR 영역 재선택
- 사용자가 직접 저장하는 플로우
- SQLite 내 JSON 페이로드 저장
- OCR 후 자동 번역
- 저장 기록 기반 학습/퀴즈 기능

## 아직 완료되지 않은 부분

- OCR 전처리는 최소 수준
- 넓은 영역 속도 최적화 필요
- OCR 정확도 튜닝 필요
- overlay.py는 코드베이스에 있지만 현재 주요 출력 경로는 아님
- 번역 정확도는 OCR 정확도에 의존
- UI에는 현재 언어 코드가 표시되며, 표시 이름 기반 콤보박스는 아직 미적용

## 번역

- deep-translator 라이브러리 사용
- 외부 번역 서비스 사용
- 인터넷 연결 필요
- 선택한 목표 언어로 OCR 결과 번역
- 번역 언어 코드는 `CORE/language_config.py`에서 관리

## 저장된 데이터

각 저장된 결과는 현재 다음과 같은 JSON 페이로드 데이터를 저장합니다.

```json
{
  "time": "2026-04-15T14:30:00",
  "content": "인식된 텍스트",
  "translation": "번역된 텍스트"
}
```

## 다음 단계

- OCR 전처리 옵션 추가
- 캡처 간격 및 OCR 설정 UI 개선
- 언어 콤보박스를 코드가 아니라 표시 이름 기준으로 개선
- EasyOCR가 여전히 무겁다면 OCR 엔진 비교
- 저장/학습 워크플로우 개선
- 번역 정확도 및 성능 개선
