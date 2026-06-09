# OCR OSS

Python `tkinter` 기반 Desktop OCR 번역/학습 앱입니다. 사용자가 화면 영역을 선택하면 해당 영역을 주기적으로 캡처하고, 이미지 변경이 감지될 때 OCR을 수행한 뒤 선택한 언어로 번역합니다. 확정된 OCR/번역 결과는 SQLite에 저장하고, 이후 학습/퀴즈 기능에 활용할 수 있습니다.

## 설치 및 실행

이 프로젝트는 `uv` 기준으로 설치하고 실행하는 것을 권장합니다.
`pip`와 `python`을 서로 다른 환경에서 사용하면 `PIL`, `mss` 같은 캡처 백엔드 의존성이 설치되어 있어도 실행 환경에서 인식되지 않을 수 있습니다.

### 1. 저장소 클론

```bash
git clone https://github.com/doo513/name_project.git
cd name_project
```

### 2. 가상환경 생성

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

### 3. 의존성 설치

```bash
uv pip install -r requirements.txt
```

### 4. 캡처 백엔드 확인

```bash
uv run python -c "from PIL import ImageGrab; import mss; print('capture backend ok')"
```

아래 문구가 출력되면 화면 캡처 백엔드가 정상적으로 설치된 상태입니다.

```text
capture backend ok
```

### 5. 실행

```bash
uv run python ocr_project/main.py
```

## 사용 흐름

1. 메인 화면에서 `원본` 언어와 `번역` 언어를 선택합니다.
2. `OCR 번역 시작`을 클릭합니다.
3. 마우스로 OCR을 수행할 화면 영역을 드래그합니다.
4. `OCR 번역 패널`이 열리고, 선택 영역을 2초마다 캡처합니다.
5. 이미지 변경이 감지되면 OCR을 수행합니다.
6. OCR 결과가 안정화되면 자동으로 번역합니다.
7. 필요하면 `다시 번역`, `레이어 재설정`, `저장`을 사용합니다.
8. 저장된 결과는 `저장 기록 보기` 또는 퀴즈 기능에서 활용합니다.

## 주요 기능

- 화면 영역 선택 기반 OCR
- 2초 주기 캡처 및 이미지 변경 감지
- OCR 결과 안정화 후 확정 처리
- 원본 언어 → 번역 언어 선택 방식 지원
- OCR 언어 코드와 번역 언어 코드 분리
- 언어 목록 단일 설정 파일 관리
- deep-translator 기반 번역
- SQLite 기반 저장
- 저장된 문장을 활용한 학습/퀴즈 기능

## 언어 설정 구조

언어 목록은 다음 파일에서만 관리합니다.

```text
ocr_project/CORE/language_config.py
```

각 언어는 하나의 `LanguageOption`으로 관리됩니다.

```python
LanguageOption("English", "en", "en", "en")
LanguageOption("Chinese Simplified", "zh-CN", "ch_sim", "zh-CN")
```

필드 의미는 다음과 같습니다.

| 필드 | 의미 |
|---|---|
| `name` | 표시용 언어 이름 |
| `code` | UI에서 선택하는 공통 언어 코드 |
| `ocr_code` | EasyOCR에 전달할 언어 코드 |
| `translation_code` | 번역 서비스에 전달할 언어 코드 |

예시 동작은 다음과 같습니다.

| 선택 방향 | OCR 언어 | 번역 방향 |
|---|---|---|
| `en -> ko` | `['en']` | `en -> ko` |
| `ko -> ja` | `['ko']` | `ko -> ja` |
| `zh-CN -> ko` | `['ch_sim']` | `zh-CN -> ko` |
| `zh-TW -> en` | `['ch_tra']` | `zh-TW -> en` |

따라서 언어를 추가하거나 코드를 수정할 때는 `main.py`나 `UI/capture_monitor.py`를 직접 수정하지 않고 `CORE/language_config.py`만 수정하면 됩니다.

## 폴더 구조

```text
ocr_project/
|- main.py
|- CORE/
|  |- app_settings.py
|  |- db.py
|  |- language_config.py
|  |- ocr_engine.py
|  |- ocr_service.py
|  |- ocr_stabilizer.py
|  |- translation_service.py
|  \- study_logic/
|- UI/
|  |- capture_monitor.py
|  |- overlay.py
|  |- quiz_ui.py
|  |- selector.py
|  |- settings_ui.py
|  \- study_list.py
\- README.md
```

## 저장 형식

저장된 OCR 기록은 일반 텍스트와 JSON 페이로드를 함께 저장합니다.

```json
{
  "time": "2026-04-15T14:30:00",
  "content": "인식된 텍스트",
  "translation": "번역된 텍스트"
}
```

## 현재 제한

- OCR 정확도는 영역 크기, 텍스트 크기, 대비, 원본 언어 선택에 따라 달라집니다.
- 너무 넓은 영역은 OCR 속도와 정확도에 불리합니다.
- 번역 품질은 OCR 결과 품질에 직접 영향을 받습니다.
- OCR 전처리는 아직 최소 수준입니다.

## 개발 예정

### 단기

- OCR 전처리 옵션 추가
- 캡처 간격과 OCR 확정 조건 UI 개선
- 저장 메타데이터 개선

### 중기

- 자막 모드와 문서 모드 분리
- OCR 엔진 비교
- 결과 필터링 및 학습 워크플로우 개선

### 장기

- OCR 결과 기반 요약 워크플로우
- GPU 또는 batch OCR 평가
- 번역 품질 개선
