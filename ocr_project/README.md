# ocr_project

Python tkinter 기반 OCR 학습 도구

---

## 최근 수정 사항 (v2.0 - 2024.04.12)

### selector.py 개선 (화면 캡처 기능 대폭 개선)

#### 기존 버전의 문제점
| 문제 | 설명 |
|------|------|
| overlay 에러 | 캡처마다 destroy/create 반복으로 TclError 발생 |
| 불안정한 캡처 루프 | 무한 루프 또는 응답 없음 현상 |
| preview_label 충돌 | 여러 곳에서 참조 정의되어 UI 업데이트 실패 |
| 복잡한 구조 | 324줄, 불필요한 중복 코드 |

#### 개선된 기능

| 기능 | 설명 |
|------|------|
| 영역 선택 UI | 반투명(30%) 오버레이 + 드래그로 영역 선택 |
| Start 버튼 | 캡처 모니터링 시작 |
| Stop 버튼 | 캡처 중지 + 텍스트 저장 |
| Reset 버튼 | 선택 초기화 |
| 실시간 미리보기 | 녹색 텍스트로 OCR 결과 표시 |
| 영역 테두리 | 파란 네모로 캡처 영역 표시 |
| 캡처 간격 | 2초마다 자동 캡처 |

#### 기술적 개선

| 개선점 | 기존 | 개선 후 |
|--------|------|---------|
| overlay 관리 | 캡처마다 destroy/create | 한 번만 생성하고 재사용 |
| 스레드 안전 | parent.after() 충돌 가능 | 메인 스레드에서만 UI 업데이트 |
| preview_label | 여러 곳에서 정의 | capture_preview 하나만 사용 |
| border 창 | overlay 안에서 복잡하게 관리 | 별도 창으로 분리 |
| 코드 라인 | 324줄 | 200줄 |
| 에러 처리 | try-pass로 조용히 실패 | 에러 로그 출력 |

#### 새로운 클래스 구조

```text
SelectorWindow
|- _create_selection_overlay()  # 영역 선택 UI 생성
|- _create_capture_ui()         # 캡처 중 실시간 미리보기
|- _create_region_border()      # 선택 영역 테두리 표시
|- _capture_loop()              # 주기적 캡처 (2초)
|- _do_capture()                # 실제 캡처 실행
|- _process_image()             # OCR 처리 (별도 스레드)
\- _update_ui()                 # UI 업데이트
```

#### 사용 방법

1. 반투명 창에서 마우스로 영역을 드래그해 선택합니다.
2. `Start` 버튼을 눌러 캡처를 시작합니다.
3. 오버레이가 숨겨지고 선택 영역 OCR이 주기적으로 실행됩니다.
4. 선택 영역 아래에서 실시간 OCR 미리보기를 확인합니다.
5. `Stop` 버튼으로 중지하고 텍스트를 저장합니다.

---

## 파일 구조

```text
ocr_project/
|- main.py                 # 프로그램 진입점 및 메인 창 관리
|- CORE/
|  |- ocr_engine.py        # EasyOCR 기반 OCR 엔진 (공유 인스턴스)
|  \- db.py                # SQLite 데이터베이스 CRUD 함수
\- UI/
   |- selector.py          # 영역 선택 UI
   |- overlay.py           # OCR 결과 표시 UI
   |- study_list.py        # 저장된 학습 데이터 목록 UI
   \- test_ui.py           # 복습/시험 기능 UI
```

## 프로젝트 개요

Python tkinter 기반의 OCR 학습 도구입니다. 사용자가 화면의 특정 영역을 선택하면 EasyOCR로 텍스트를 자동 인식하고, 그 결과를 확인 및 수정한 후 SQLite 데이터베이스에 저장할 수 있습니다. 모든 모듈은 `CORE/`와 `UI/`로 분리되어 있으며, 각 UI 모듈은 독립적으로 실행 가능합니다.

---

## 1. main.py

프로그램 진입점이며 메인 창과 각 기능 창의 연결을 담당합니다.

- 영역 선택 UI 열기
- OCR 결과 오버레이 열기
- 학습 목록 열기
- 복습/시험 UI 열기

## 2. selector.py

화면 영역 선택과 주기적 OCR 캡처를 담당합니다.

- 반투명 전체화면 오버레이
- 드래그 기반 영역 선택
- Start/Stop/Reset 제어
- 선택 영역 테두리 표시
- 실시간 OCR 미리보기

## 3. overlay.py

OCR 결과 표시 및 저장 UI입니다.

- OCR 텍스트 표시 및 편집
- 클립보드 복사
- SQLite 저장
- 저장 실패 시 텍스트 파일 저장 폴백

## 4. ocr_engine.py

EasyOCR 래퍼입니다.

- 기본 언어: 한글 + 영문
- `read_text(image_path)`
- `read_text_simple(image_path)`
- numpy array 직접 처리 지원
- 공유 인스턴스 패턴 사용

## 5. db.py

SQLite 데이터베이스 관리 모듈입니다.

- `init_db()`
- `save_ocr_result(content, source_region, tags)`
- `list_ocr_results(limit)`
- `search_ocr_results(keyword)`
- `delete_ocr_result(ocr_id)`

데이터베이스 파일은 `CORE/ocr_study.db`입니다.

## 6. study_list.py

저장된 OCR 결과 목록을 조회하는 화면입니다.

- 저장 결과 조회
- 목록 표시
- 추후 필터링/검색/정렬 확장 가능

## 7. test_ui.py

DB 기반 학습 데이터로 복습/시험 흐름을 구성하는 UI입니다.

- OCR 결과를 문제 데이터로 활용
- 사용자 입력과 정답 비교
- 학습 진행 추적

## 의존성

리포지토리 루트의 `requirements.txt`를 사용합니다.

- EasyOCR
- opencv-python
- Pillow
- numpy

---

## 실행 방법

리포지토리 루트에서 의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

그 다음 앱을 실행합니다.

```bash
cd ocr_project
python main.py
```

## 기본 사용 흐름

1. `Open Region Selector`로 캡처 영역을 선택합니다.
2. `Open Overlay`로 OCR 결과를 확인하고 수정합니다.
3. `Save`로 SQLite 또는 텍스트 파일에 저장합니다.
4. `Open Study List`로 저장된 데이터를 확인합니다.
5. `Open Test UI`로 복습/시험 기능을 실행합니다.

---

## 현재 구현 현황

### 완료된 기능

- 영역 선택 UI
- 화면 캡처 및 OCR 처리
- OCR 결과 표시 및 편집
- 텍스트 저장/복사
- SQLite 데이터베이스 저장
- CORE/UI 구조 분리

### 진행 중 또는 예정 기능

- study_list.py 추가 고도화
- test_ui.py 학습 흐름 개선
- 자동 문제 생성 알고리즘
- UI/UX 개선
- 추가 언어 지원

---

## 기술 스택

- GUI: Python tkinter
- OCR: EasyOCR
- Database: SQLite3
- Image: Pillow, OpenCV
- Language: Python 3.8+
