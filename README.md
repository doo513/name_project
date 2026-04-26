# OCR OSS

Python `tkinter`로 만든 Desktop 앱입니다. 화면 영역을 선택하고 주기적으로 캡처하며, 이미지가 변경될 때마다 OCR을 수행합니다.

## 설치 및 실행

### 1. 설치

```bash
pip install -r requirements.txt
```

### 2. 실행

```bash
cd ocr_project
python main.py
```

### 3. 사용 방법

1. `Open Region Selector` 클릭
2. 마우스로 OCR 영역 드래그
3. `Capture OCR Panel`이 2초마다 해당 영역 캡처
4. 이미지가 변경되면 자동으로 OCR 수행, 또는 `Recognize Now` 수동 클릭
5.Panel에 최신 OCR 결과만 표시
6. `Save` 클릭하여 데이터베이스에 저장
7. `Study List`로 저장된 결과 확인

## 주요 기능

- 영역 선택과 OCR 실행 분리
- 캡처와 OCR 모듈 분리
- 이미지 변경 감지 후 OCR 실행 (불필요한 반복 방지)
- 수동 인식 (`Recognize Now`)
- 원본 언어 선택 → 번역 언어 선택 번역 기능
- SQLite 데이터베이스에 JSON 형식으로 저장

## 저장 형식

저장된 OCR 기록은 일반 텍스트와 JSON 페이로드를 함께 저장합니다.

```json
{
  "time": "2026-04-15T14:30:00",
  "content": "인식된 텍스트"
}
```

## 폴더 구조

```text
ocr_project/
|- main.py
|- CORE/
|  |- db.py
|  |- ocr_engine.py
|  |- ocr_service.py
|  \- translation_service.py
\- UI/
   |- capture_monitor.py
   |- selector.py
   |- study_list.py
   |- test_ui.py
   \- overlay.py
```

## 디자인 notes

- 화면 캡처는 상대적으로 빠름, OCR이 expensive한 작업
- 이전 프레임과 비교하여 이미지 변경时才 OCR 실행
- 결과는 누적되지 않고, 사용자가 저장할 때마다 최신 결과만 메모리에 유지

## 현재 제한

- OCR 정확도는 영역 크기, 텍스트 크기, 대비, 선택한 언어 쌍에 따라 달라짐
- 너무 넓은 영역은 느리고 정확도도 낮음

## 개발 예정

### 단기

- OCR 전처리 (拡大, 그레이스케일, 대비,_threshold)
- 캡처 간격 및 OCR 옵션 UI 노출
- 저장 메타데이터 개선

### 중기

- 자막 모드와 문서 모드 분리
- OCR 엔진 비교
- 결과 필터링 및 학습 워크플로우 개선

### 장기

- OCR 결과 기반 번역 및 요약 워크플로우
- GPU 또는_batch OCR 평가