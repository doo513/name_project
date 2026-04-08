# ocr_study_app

Python tkinter 기반 OCR 학습 도구

## 파일 구조

```
ocr_project/
├── main.py                 # 프로그램 진입점 및 메인 창 관리
├── requirements.txt        # 프로젝트 의존성
├── CORE/
│   ├── ocr_engine.py      # EasyOCR 기반 OCR 엔진 (공유 인스턴스)
│   └── db.py              # SQLite 데이터베이스 CRUD 함수
└── UI/
    ├── selector.py        # 영역 선택 UI - 마우스 드래그로 캡처 영역 선택
    ├── overlay.py         # OCR 결과 표시 UI - 텍스트 표시 및 저장/복사/닫기
    ├── study_list.py      # 저장된 학습 데이터 목록 UI
    └── test_ui.py         # 복습/시험 기능 UI
```

## 프로젝트 개요

Python tkinter 기반의 OCR 학습 도구입니다. 사용자가 화면의 특정 영역을 선택하면 EasyOCR로 텍스트를 자동 인식하고, 그 결과를 확인 및 수정한 후 SQLite 데이터베이스에 저장할 수 있습니다. 모든 모듈은 `CORE/` (비즈니스 로직)과 `UI/` (사용자 인터페이스)로 명확히 분리되어 있으며, 각 UI 모듈은 독립적으로 실행 가능합니다.

---

## 1. main.py

**프로그램 시작 및 메인 화면 관리**

- 프로그램의 진입점 역할
- 메인 창 생성 및 UI 버튼 구성
- 4가지 기능별 창 열기:
  - **영역 선택** (selector.py) - 화면 캡처 영역 선택
  - **OCR 결과** (overlay.py) - OCR 인식 결과 표시 및 저장
  - **학습 목록** (study_list.py) - 저장된 데이터 조회
  - **시험/복습** (test_ui.py) - 학습 기능
- 각 창 간의 데이터 통신 처리 (선택한 영역, OCR 결과 등)

**현재 상태**: ✅ 완전히 구현됨

---

## 2. selector.py (UI/selector.py)

**화면 영역 선택 기능**

- 전체 화면을 반투명한 검은색 오버레이로 표시
- 마우스 드래그를 통해 캡처할 영역 선택
- 선택된 영역을 PNG 파일로 저장
- **공유 OCR 엔진**을 사용하여 자동으로 OCR 처리
- OCR 결과를 overlay.py로 전달하여 표시
- ESC 키로 취소, Enter/더블클릭으로 확정

**현재 상태**: ✅ 완전히 구현됨

---

## 3. overlay.py (UI/overlay.py)

**OCR 결과 표시 및 관리**

- EasyOCR을 통해 인식된 텍스트를 표시/편집
- 사용자가 인식 결과 수정 가능
- 구현된 기능:
  - **저장** (Save): `CORE.db`의 `save_ocr_result()` 함수를 사용하여 SQLite에 저장. 실패 시 사용자가 선택한 경로로 .txt 파일로 저장
  - **복사** (Copy): 인식된 텍스트를 클립보드로 복사
  - **닫기** (Close): 창 종료
- 저장 시 영역 정보(source_region)도 함께 기록

**현재 상태**: ✅ 완전히 구현됨

---

## 4. ocr_engine.py (CORE/ocr_engine.py)

**EasyOCR 기반 OCR 엔진 (공유 인스턴스 패턴)**

- EasyOCR 라이브러리를 래핑한 OCR 엔진
- 지원 언어: 영문, 러시아어, 아랍어, 한글 (기본값)
- 주요 기능:
  - `read_text(image_path)` - 이미지에서 텍스트와 신뢰도 점수 추출
  - `read_text_simple(image_path)` - 텍스트만 추출
- **공유 인스턴스**: `get_ocr_engine()` 함수를 통해 전역 인스턴스 관리
  - 첫 호출 시 OCREngine 생성, 이후 재사용
  - selector.py에서 사용
- 모듈화된 구조로 향후 다른 OCR 엔진 교체 용이

**현재 상태**: ✅ 완전히 구현됨

---

## 5. db.py (CORE/db.py)

**SQLite 데이터베이스 관리**

- SQLite 데이터베이스 생성 및 CRUD 연산 제공
- 주요 함수:
  - `init_db()` - ocr_results 테이블 생성
  - `save_ocr_result(content, source_region, tags)` - OCR 결과 저장
  - `list_ocr_results(limit)` - 저장된 모든 결과 조회
  - `search_ocr_results(keyword)` - 키워드로 검색
  - `delete_ocr_result(ocr_id)` - 데이터 삭제
- 데이터 구조: id, content, source_region, tags, created_at
- 데이터베이스 파일: `CORE/ocr_study.db`

**현재 상태**: ✅ 완전히 구현됨

---

## 6. study_list.py (UI/study_list.py)

**저장된 학습 데이터 목록 화면**

- `CORE.db`의 함수를 사용하여 저장된 OCR 결과 조회 및 표시
- 향후 추가될 기능:
  - 필터링 및 검색
  - 정렬 (날짜, 카테고리 등)
  - 데이터 수정/삭제
  - 개별 데이터 상세 보기

**현재 상태**: 🔄 UI 골격 구현 중, 기본 표시 기능 추가 필요

---

## 7. test_ui.py (UI/test_ui.py)

**복습/시험 기능**

- 현재: UI 골격 및 더미 데이터 기반 구조 (미완성)
- 향후 구현 계획:
  - `CORE.db`의 저장된 OCR 결과를 학습 데이터로 활용
  - 자동 문제 생성 (OCR 결과 → 객관식/주관식 문제)
  - 사용자 정답과 비교 및 채점
  - 학습 진행률 추적

**현재 상태**: 🔄 UI 골격만 존재, 기능 구현 필요

---

## 8. requirements.txt

**프로젝트 의존성**

필수 라이브러리:
- `EasyOCR`: 텍스트 인식 엔진
- `tkinter`: GUI 프레임워크 (Python 기본 포함)
- `Pillow`: 이미지 처리
- `opencv-python`: 이미지 전처리
- `numpy`: 수치 계산

---

## 현재 구현 현황

### ✅ 완료된 기능
- ✅ 영역 선택 UI (selector.py) - 마우스 드래그로 영역 선택
- ✅ 화면 캡처 기능 - PNG 파일로 저장
- ✅ EasyOCR 통합 - 한글/영문/러시아어/아랍어 인식
- ✅ OCR 결과 표시 및 편집 (overlay.py)
- ✅ 텍스트 저장/복사 기능
- ✅ SQLite 데이터베이스 구현 (CORE/db.py)
- ✅ 공유 OCR 엔진 (singleton 패턴) - 메모리 효율
- ✅ 모듈 구조 분리 (CORE/, UI/)
- ✅ 완전한 import 경로 설정

### 🔄 진행 중/예정 기능
- 🔄 study_list.py - 데이터 조회 및 표시 기능 추가
- 🔄 test_ui.py - 복습/시험 기능 구현
- ⏳ 자동 문제 생성 알고리즘
- ⏳ 사용자 정답 채점 시스템
- ⏳ UI/UX 개선
- ⏳ 신뢰도 점수 표시
- ⏳ 다양한 언어 확대

---

## 아키텍처

### 계층 분리
- **UI 계층** (`UI/`): tkinter 기반 사용자 인터페이스
  - main.py - 메인 창 및 네비게이션
  - selector.py - 영역 선택
  - overlay.py - 결과 표시 및 저장
  - study_list.py - 데이터 목록
  - test_ui.py - 복습/시험
  
- **비즈니스 로직 계층** (`CORE/`): 핵심 기능 구현
  - ocr_engine.py - OCR 처리 (EasyOCR 래핑)
  - db.py - 데이터 저장/조회

### 데이터 흐름
```
selector.py (캡처)
    ↓
ocr_engine.py (OCR 처리)
    ↓
overlay.py (결과 표시/편집)
    ↓
db.py (데이터 저장)
    ↓
study_list.py (데이터 조회)
```

### 디자인 패턴
- **공유 인스턴스**: `get_ocr_engine()` - OCREngine 싱글톤
- **모듈화**: CORE/UI 명확한 분리로 유지보수 용이
- **에러 처리**: 데이터베이스 저장 실패 시 파일 저장 폴백

---

## 실행 방법

### 필수 설치
```bash
pip install -r requirements.txt
```

### 프로그램 시작
```bash
python main.py
```

### 기본 사용 흐름
1. **Open Region Selector** 클릭 → 화면에서 텍스트 영역 드래그로 선택
2. **Open Overlay** 클릭 → OCR 인식 결과 확인 및 수정
3. **Save** 버튼 → SQLite 데이터베이스 또는 텍스트 파일로 저장
4. **Open Study List** 클릭 → 저장된 데이터 확인 (준비 중)
5. **Open Test UI** 클릭 → 복습/시험 기능 사용 (개발 중)

---

## 향후 계획

1. **study_list.py 완성**
   - 저장된 OCR 결과 목록 표시
   - 검색/필터링 기능
   - 데이터 수정/삭제 기능

2. **test_ui.py 구현**
   - 저장된 데이터로 학습 문제 생성
   - 자동 채점 시스템
   - 학습 진도 추적

3. **OCR 엔진 개선**
   - 추가 언어 지원 (중국어, 일본어 등)
   - 손글씨 인식 기능

4. **사용자 인터페이스**
   - 다크 모드 지원
   - 반응형 디자인 개선
   - 설정 화면 추가

5. **성능 최적화**
   - OCR 처리 속도 개선
   - 메모리 사용량 최적화
   - 캐싱 메커니즘 추가

---

## 기술 스택

- **GUI**: Python tkinter
- **OCR**: EasyOCR
- **데이터베이스**: SQLite3
- **이미지 처리**: Pillow, OpenCV
- **언어**: Python 3.8+
