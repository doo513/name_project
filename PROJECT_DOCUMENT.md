# OCR OSS 프로젝트 문서

## 1. 개요

Python tkinter로 만든 Desktop OCR 앱입니다. 화면 영역을 선택하고 주기적으로 캡처하며, 이미지가 변경될 때마다 OCR을 수행합니다.

## 2. 아키텍처

```
ocr_project/
├── main.py                    # Main Window + OCR/언어 선택
├── CORE/
│   ├── ocr_engine.py        # EasyOCR 래핑
│   ├── ocr_service.py       # OCR 실행 + 결과 정리
│   ├── translation_service.py  # deep-translator 번역
│   └── db.py                # SQLite 저장
└── UI/
    ├── selector.py          # 영역 선택 (마우스 드래그)
    ├── capture_monitor.py  # Panel - 주기적 캡처 + 버튼
    ├── study_list.py     # 저장된 결과 목록
    ├── test_ui.py      # 테스트용
    └── overlay.py     # 오버레이
```

## 3. 작동 방식

```
1. Open Region Selector
   └─ 마우스로 영역 드래그

2. Panel 열림 (2초마다 캡처)
   └─ 이미지 변경 감지 → OCR 실행

3. OCR (ocr_service.py)
   └─ EasyOCR → 결과 정리 (clean_ocr_text)

4. Translate 버튼
   └─ 원본 → 번역 (deep-translator)

5. Save 버튼
   └─ SQLite에 JSON 저장
```

## 4. 주요 기능

### 4.1 OCR 언어 선택
- 원본 언어 (예: en, ko, ja, zh)
- 번역 언어 (예: ko, en, ja, zh)
- 형식: `원본 → 번역`

### 4.2 OCR 결과 정리
- 빈 줄 제거
- 앞뒤 공백 제거
- 연결된 단어 처리 (영문/숫자/따옴표)

### 4.3 번역
- deep-translator 사용 (로컬)
- 원본 → 번역 언어

### 4.4 저장
- SQLite에 JSON 형식으로 저장
- time, content, translation 포함

## 5. 커밋 히스토리

| 날짜 | 커밋 | 내용 |
|------|------|------|
| 2026-04-27 | 01335d3 | Fix import issues: add __init__.py files |
| 2026-04-27 | d97dad1 | Fix code issues: ocr_service, translation_service |
| 2026-04-27 | 5306c1f | OCR + 번역 자동 기능 추가 |
| 2026-04-26 | 781726d | 한자 제거하고 순한글로 수정 |
| 2026-04-26 | 0616665 | OCR 결과 정리 (연결된 단어 병합) |
| 2026-04-26 | 5a04992 | OCR 결과 정리 (빈 줄/공백 제거) |
| 2026-04-26 | d6a0978 | README 한국어로 업데이트 |
| 2026-04-26 | 2016417 | 번역 기능 추가 (원본→번역 선택) |
| 2026-04-15 | ac2d255 | 영역 선택 및 패딩 수정 |
| 2026-04-15 | ce32d60 | 캡처/OCR 분리 + JSON 저장 |
| 2026-04-14 | 3fd380e | 중복 디렉토리 제거 |

## 6. 주요 구현 내용 (2026-04-26~27)

### 6.1 번역 기능 추가 (2026-04-26)
- TranslationService 추가 (deep-translator 사용)
- 원본 언어, 번역 언어 선택 UI
- Panel에서 번역 버튼

### 6.2 OCR 결과 정리 (2026-04-26)
- clean_ocr_text() 함수 추가
- 빈 줄, 공백 제거
- 연결된 단어 병합

### 6.3 UI 간소화 (2026-04-26)
- OCR Language Pair 제거
- 원본 → 번역 형태로 변경

### 6.4 README 수정 (2026-04-26)
- 한국어로 재작성
- 한자 제거

## 7. 비교 분석

### ours (main) vs main_3

| 항목 | main (우리가) | main_3 |
|------|-------------|--------|
| ocr_service.py | 93줄 (단순) | 421줄 (복잡) |
| image processing | 없음 | 있음 (PIL) |
| translation | 별도 파일 | ocr_service에 합침 |
| 구조 | 깔끔 | 복잡 |
| 성능 | 빠름 | 느릴 수 있음 |

**우리의 장점:**
- 유지보수가 쉬움
- 속도가 빠름
- 기능 분리되어 있음

## 8. 사용 방법

### 설치
```bash
pip install -r requirements.txt
```

### 실행
```bash
cd ocr_project
python main.py
```

### 사용 흐름
1. `Open Region Selector` 클릭
2. 마우스로 OCR 영역 드래그
3. 원본 언어, 번역 언어 선택
4. `Recognize Now` 클릭
5. `Translate` 클릭
6. `Save` 클릭

## 9. 업데이트 예정

### 단기
- OCR 후처리 개선 (연결된 단어 분리)
- 텍스트 위치 정보 사용

### 중기
- 자막 모드 / 문서 모드
- 결과 필터링 개선

### 장기
- GPU OCR 평가
- 요약 기능