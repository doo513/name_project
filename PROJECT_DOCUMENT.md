# OCR OSS 프로젝트 문서

## 1. 개요

Python `tkinter`로 만든 Desktop OCR 번역/학습 앱입니다. 사용자가 화면 영역을 선택하면 해당 영역을 주기적으로 캡처하고, 이미지 변경이 감지될 때 OCR을 수행합니다. OCR 결과가 안정화되면 선택한 목표 언어로 번역하고, 확정된 OCR/번역 결과를 SQLite에 저장합니다.

이번 구조에서는 언어 선택 로직을 `CORE/language_config.py`로 분리했습니다. UI에서 선택하는 언어 코드, EasyOCR에 전달하는 OCR 코드, 번역 서비스에 전달하는 번역 코드를 한 곳에서 관리합니다.

## 2. 아키텍처

```text
ocr_project/
├── main.py                       # 메인 창, 캡처/OCR/번역 흐름 제어
├── CORE/
│   ├── app_settings.py           # OCR 확정 조건 등 설정값
│   ├── db.py                     # SQLite 저장 및 조회
│   ├── language_config.py        # 언어 목록, OCR 코드, 번역 코드 단일 관리
│   ├── ocr_engine.py             # EasyOCR 래핑
│   ├── ocr_service.py            # OCR 실행 및 결과 정리
│   ├── ocr_stabilizer.py         # OCR 후보 안정화/확정 로직
│   ├── translation_service.py    # deep-translator 번역
│   └── study_logic/              # 문제 로드, 채점 기준, 풀이 기록, 오답 관리
└── UI/
    ├── selector.py               # 영역 선택 UI
    ├── capture_monitor.py        # OCR 번역 패널, 주기적 캡처, 버튼 처리
    ├── quiz_ui.py                # 퀴즈 UI
    ├── settings_ui.py            # OCR 확정 조건 설정 UI
    ├── study_list.py             # 저장된 결과 목록
    └── overlay.py                # 보조 오버레이 코드
```

## 3. 작동 방식

```text
1. 메인 화면에서 원본 언어와 번역 언어 선택
   └─ 예: en -> ko, ko -> ja, ja -> ko

2. `OCR 번역 시작` 클릭
   └─ 마우스로 OCR 영역 드래그

3. `OCR 번역 패널` 열림
   └─ 메인 화면의 언어 선택값이 패널로 전달됨
   └─ 선택 영역을 2초마다 캡처

4. 이미지 변경 감지
   └─ 동일 프레임이면 OCR 생략
   └─ 변경된 프레임이면 OCR 작업 시작

5. OCR 수행
   └─ OCRService는 원본 언어만 사용
   └─ 번역 대상 언어는 OCR 엔진에 넣지 않음

6. OCR 후보 안정화
   └─ OCRStabilizer가 같은 문장이 반복되는지 확인
   └─ 확정 전에는 Stabilizing 상태로 표시

7. 번역 수행
   └─ TranslationService가 확정 원문을 목표 언어로 번역

8. 저장
   └─ 사용자가 `저장`을 누르면 OCR 원문/번역문을 SQLite에 저장
```

## 4. 언어 설정 구조

### 4.1 단일 관리 파일

언어 목록은 다음 파일에서만 관리합니다.

```text
CORE/language_config.py
```

`main.py`, `UI/capture_monitor.py`에 언어 리스트를 직접 작성하지 않습니다. 두 파일은 `LANGUAGE_CODES`, `DEFAULT_SOURCE_LANGUAGE`, `DEFAULT_TARGET_LANGUAGE` 등을 import해서 사용합니다.

### 4.2 LanguageOption 구조

```python
@dataclass(frozen=True)
class LanguageOption:
    name: str
    code: str
    ocr_code: str
    translation_code: str
```

| 필드 | 역할 |
|---|---|
| `name` | 표시용 언어 이름 |
| `code` | UI에서 사용하는 공통 선택 코드 |
| `ocr_code` | EasyOCR에 전달하는 코드 |
| `translation_code` | 번역 서비스에 전달하는 코드 |

### 4.3 현재 언어 예시

```python
LanguageOption("Korean", "ko", "ko", "ko")
LanguageOption("English", "en", "en", "en")
LanguageOption("Japanese", "ja", "ja", "ja")
LanguageOption("Chinese Simplified", "zh-CN", "ch_sim", "zh-CN")
LanguageOption("Chinese Traditional", "zh-TW", "ch_tra", "zh-TW")
```

### 4.4 OCR과 번역의 분리

| 사용자가 선택한 방향 | OCRService에 전달 | TranslationService에 전달 |
|---|---|---|
| `en -> ko` | `['en']` | `en -> ko` |
| `ko -> ja` | `['ko']` | `ko -> ja` |
| `ja -> ko` | `['ja']` | `ja -> ko` |
| `zh-CN -> ko` | `['ch_sim']` | `zh-CN -> ko` |
| `zh-TW -> en` | `['ch_tra']` | `zh-TW -> en` |

이전 구조처럼 `[원본 언어, 번역 대상 언어]`를 OCR 엔진에 함께 넣지 않습니다. OCR 엔진은 화면에 실제로 있는 원본 언어만 인식하면 됩니다.

### 4.5 하위 호환 처리

이전 값과의 충돌을 줄이기 위해 별칭을 둡니다.

```python
LANGUAGE_ALIASES = {
    "zh": "zh-CN",
    "ch_sim": "zh-CN",
    "ch_tra": "zh-TW",
}
```

따라서 과거 UI나 설정에서 `zh`, `ch_sim`, `ch_tra`가 들어와도 내부적으로 현재 코드 체계로 변환됩니다.

## 5. 주요 기능

### 5.1 OCR 언어 선택

- 원본 언어와 번역 언어를 별도로 선택
- 형식: `원본 -> 번역`
- OCR에는 원본 언어만 사용
- 번역에는 원본 언어와 번역 언어를 함께 사용

### 5.2 OCR 결과 정리

- 빈 줄 제거
- 앞뒤 공백 제거
- 연결된 단어 처리
- 영문/숫자/따옴표 주변 줄 병합

### 5.3 OCR 안정화

- 2초 주기 캡처
- OCR 결과가 바로 확정되지 않고 후보로 처리됨
- 동일하거나 유사한 결과가 반복되면 확정
- 확정 이후 번역 수행

### 5.4 번역

- deep-translator 사용
- 외부 번역 서비스 필요
- 선택한 목표 언어로 OCR 결과 번역

### 5.5 저장

- SQLite에 JSON 형식으로 저장
- `time`, `content`, `translation` 포함

## 6. 최근 구조 변경 내용

### 6.1 언어 설정 파일 추가

`CORE/language_config.py`를 추가하여 언어 목록을 한 곳에서 관리하도록 변경했습니다.

### 6.2 OCR 언어와 번역 언어 분리

기존에는 원본 언어와 번역 대상 언어를 함께 OCR 언어 목록으로 넘길 수 있었습니다. 수정 후에는 OCR에는 원본 언어만 전달하고, 번역 단계에서만 원본/목표 언어를 사용합니다.

### 6.3 메인 화면과 캡처 패널 언어 상태 동기화

메인 화면에서 선택한 언어 방향이 `open_capture_monitor()`를 통해 캡처 패널로 전달됩니다. 따라서 메인 화면에서 `ko -> ja`를 선택하고 시작하면 캡처 패널도 같은 방향으로 열립니다.

### 6.4 중복 언어 리스트 제거

`main.py`와 `UI/capture_monitor.py`에 있던 하드코딩 언어 목록을 제거하고 `LANGUAGE_CODES`를 사용하도록 변경했습니다.

## 7. 커밋 히스토리

| 날짜 | 커밋 | 내용 |
|------|------|------|
| 2026-06-09 | local | 언어 설정 단일화, OCR/번역 언어 코드 분리 |
| 2026-04-27 | 01335d3 | Fix import issues: add __init__.py files |
| 2026-04-27 | d97dad1 | Fix code issues: ocr_service, translation_service |
| 2026-04-27 | 5306c1f | OCR + 번역 자동 기능 추가 |
| 2026-04-26 | 781726d | 한자 제거하고 순한글로 수정 |
| 2026-04-26 | 0616665 | OCR 결과 정리 |
| 2026-04-26 | d6a0978 | README 한국어로 업데이트 |
| 2026-04-26 | 2016417 | 번역 기능 추가 |
| 2026-04-15 | ac2d255 | 영역 선택 및 패딩 수정 |
| 2026-04-15 | ce32d60 | 캡처/OCR 분리 + JSON 저장 |
| 2026-04-14 | 3fd380e | 중복 디렉토리 제거 |

## 8. 비교 분석

### ours(main) vs main_3

| 항목 | main | main_3 |
|------|------|--------|
| OCR 서비스 | `ocr_service.py` 중심 | OCR/전처리 기능이 더 복잡하게 결합 |
| 번역 | `translation_service.py`로 분리 | OCR 서비스에 합쳐질 가능성 높음 |
| 언어 설정 | `language_config.py`에서 단일 관리 | 파일별 분산 가능성 |
| 구조 | UI/OCR/번역/DB 분리 | 기능 결합도가 높을 수 있음 |
| 유지보수 | 언어 추가와 수정이 쉬움 | 언어 코드 변경 시 여러 파일 수정 필요 |

## 9. 사용 방법

### 설치

이 프로젝트는 `uv` 환경 기준으로 설치합니다. `pip install`과 일반 `python` 실행을 섞으면 실행 중인 Python에 `Pillow`, `mss`, `easyocr`가 설치되지 않는 문제가 생길 수 있습니다.

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

의존성 설치:

```bash
uv pip install -r requirements.txt
```

캡처 백엔드 확인:

```bash
uv run python -c "from PIL import ImageGrab; import mss; print('capture backend ok')"
```

### 실행

```bash
uv run python ocr_project/main.py
```

### 사용 흐름

1. 원본 언어와 번역 언어 선택
2. `OCR 번역 시작` 클릭
3. 마우스로 OCR 영역 드래그
4. OCR 확정 결과와 번역 결과 확인
5. 필요하면 `다시 번역` 또는 `레이어 재설정` 사용
6. `저장` 클릭

## 10. 업데이트 예정

### 단기

- OCR 전처리 개선
- 캡처 간격 및 OCR 확정 조건 UI 개선
- 언어 콤보박스를 코드가 아니라 표시 이름 기준으로 개선

### 중기

- 자막 모드 / 문서 모드 분리
- 결과 필터링 개선
- 저장 데이터 기반 학습 기능 강화

### 장기

- GPU OCR 평가
- 요약 기능
- 번역 품질 개선
