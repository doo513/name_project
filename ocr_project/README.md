# -sw-

Python tkinter 구조

파일 
- main.py: 전체 실행 및 화면 연결
- selector.py: 영역 선택 UI
- overlay.py: OCR 결과 표시 UI (저장/복사/닫기 버튼)
- db.py: SQLite 저장/조회
- study_list.py: 저장 목록 UI
- test_ui.py: 테스트 UI

- 처음에는 UI 골격과 함수 구조만 작성
- 더미 데이터 사용
- 각 파일은 import 가능한 구조로 작성
-나중에 기능이 더 많아지거나 추가되면 ui/, core/, db/로 분리하려고함


1. main.py 

프로그램 시작
메인 창 만들기
버튼으로 각 화면 열기
나중에 화면끼리 연결

main.py
 ├─ 영역 선택 창 열기
 ├─ 결과 창 열기
 ├─ 학습 리스트 열기
 └─ 테스트 창 열기

2. selector.py

영역 선택 UI
마우스로 드래그하여 화면의 특정 영역 선택
선택된 좌표를 main으로 전달

3. overlay.py

OCR 결과 표시 UI
텍스트 표시
저장 / 복사 / 닫기 기능 제공
향후 OCR 결과를 실제로 표시하는 핵심 화면

4. db.py

SQLite 기반 데이터 저장/조회 구조
현재는 기본 구조만 구현
이후 OCR 결과 및 학습 데이터 저장 담당

5. study_list.py

저장된 데이터 목록 UI
학습 데이터 확인 화면
향후 필터/검색/정렬 기능 추가 예정

6.test_ui.py

복습 / 시험 UI
현재는 UI 골격과 더미 데이터 기반 구조로만 만들었음(아직 미완성)
추후 DB와 연결하여 문제 생성 예정
test.ui는 나중에 DB 기반으로 바꿔야함(저장된 OCR 결과를 학습 데이터로 다시 쓰는 구조)
