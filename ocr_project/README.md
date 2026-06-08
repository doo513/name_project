# ocr_project

Python tkinter로 만든 Desktop OCR 학습 앱입니다.

## 사용 방법

1. `python main.py` 실행
2. `Open Region Selector` 클릭
3. 마우스로 캡처 영역 드래그
4. `Capture OCR Panel`에서 최신 OCR 결과 확인
5. `Recognize Now`로 수동 OCR
6. `Save` 클릭하여 데이터베이스에 저장

## 현재 구조

```
main.py
|- UI.selector            # 영역 선택 오버레이
|- UI.capture_monitor     # 주기적 캡처 패널 및 결과 표시
|- CORE.ocr_service      # 이미지를 OCR 텍스트로 변환 + 번역
|- CORE.db               # 로컬 데이터베이스 저장 및 查询
|- UI.study_list         # 저장된 결과 목록
\- UI.test_ui            # 테스트 / 검토 UI
```

## 현재 상태

### 동작 중

- 마우스로 영역 선택
- 2초 주기 캡처
- 변경 감지 후 OCR
- 사용자 선택 가능한 2개 언어 OCR 쌍
- 수동 인식 버튼
- 사용자触发 저장 플로우
- SQLite 내 JSON 페이로드 저장
- OCR → 번역 파이프라인 (deep-translator 기반)
- OCR 후 자동 번역

### 아직 완료되지 않음

- OCR 전처리 여전히 최소
- 넓은 영역 속도 최적화 안 됨
- OCR 정확도 튜닝 필요
- overlay.py는 코드베이스에 있지만 더 이상 주요 출력 경로 아님
- 번역 정확도는 OCR 정확도에 의존

## 번역

- deep-translator 라이브러리 사용
- 자동 언어 감지 지원
- 외부 번역 서비스 사용 (Google Translate 등)
- 인터넷 연결 필요
- 선택한 목표 언어로 OCR 결과 번역

## 저장된 데이터

각 저장된 결과는 현재 다음과 같은 JSON 페이로드 데이터를 저장합니다:

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
- EasyOCR가 여전히 무겁다면 OCR 엔진 비교
- 저장 / 학습 워크플로우 개선
- 번역 정확도 및 성능 개선