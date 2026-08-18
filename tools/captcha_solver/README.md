# CTF CAPTCHA Solver

`captcha-handout.zip`에 포함된 Roboto Mono 4종과 저장소의 기존 OCR 스택(EasyOCR/OpenCV/Pillow)을 이용해 웹 CAPTCHA를 연속으로 푸는 실험용 CTF 도구입니다.

현재 확인된 챌린지 프로토콜은 다음과 같습니다.

```text
/start
  -> 브라우저 app.js가 token / round_nonce 관리
/captcha
  -> image/png (240x80)
  -> 브라우저에서는 blob: URL로 표시
/submit
  POST JSON:
  {
    "token": state.token,
    "answer": elements.answer.value.toLowerCase(),
    "round_nonce": state.roundNonce
  }

응답 예:
{
  "correct": true,
  "streak": 1,
  "target": 60,
  "qualified": false,
  "solved": false
}
```

## 설계

`token`, `round_nonce`, `authHeaders()`를 Python에서 다시 구현하지 않습니다. Playwright로 실제 페이지를 실행하고 사이트의 `app.js`가 인증/라운드 상태를 계속 관리하게 둡니다.

Solver는 다음 순서로 동작합니다.

1. 네트워크에서 실제 `/captcha` PNG 응답을 가로챕니다.
2. 6자리 `a-z0-9` 문자열을 판독합니다.
3. 페이지의 answer input에 값을 입력하고 Enter로 원래 submit handler를 실행합니다.
4. `/submit` JSON의 `correct`, `streak`, `target`, `solved`를 확인한 후 다음 `/captcha`를 처리합니다.

이 방식은 화면의 `blob:` URL을 직접 요청하지 않으며, 라운드마다 바뀌는 nonce를 별도로 복사할 필요도 없습니다.

## OCR 방식

기본값 `--engine hybrid`는 두 경로를 같이 사용합니다.

- **template**: 핸드아웃의 정확한 Roboto Mono 4종을 여러 크기/회전으로 렌더링하여 OpenCV로 비교
- **easyocr**: 저장소가 이미 사용하는 EasyOCR을 `a-z0-9` allowlist로 제한하여 전체 문자열 인식

두 결과가 일치하면 그대로 사용합니다. EasyOCR이 높은 확신도의 정확히 6자리 결과를 주면 이를 우선할 수 있고, 그렇지 않으면 exact-font template 결과를 사용합니다.

60연속 정답 문제이므로 기본적으로 confidence가 낮으면 틀린 답을 보내서 streak를 초기화하는 대신 중단하고 `captcha_debug/`에 샘플을 남깁니다.

## 설치

저장소 루트에서:

```powershell
git clone https://github.com/doo513/name_project.git
cd name_project

py -m pip install -r tools/captcha_solver/requirements.txt
py -m playwright install chromium
```

핸드아웃은 저장소 루트에 두는 것이 가장 간단합니다.

```text
name_project/
├─ captcha-handout.zip
├─ requirements.txt
└─ tools/
   └─ captcha_solver/
      └─ solve.py
```

폰트는 실행 중 `.fonts_cache/`에 자동 추출되며 Git에는 포함되지 않습니다.

## 먼저 이미지 하나 판독

실제 CAPTCHA PNG를 저장했다면 원격 제출 없이 OCR만 검사할 수 있습니다.

```powershell
py tools/captcha_solver/solve.py `
  --handout captcha-handout.zip `
  --image captcha.png `
  --expected-len 6
```

특정 엔진만 비교하려면:

```powershell
py tools/captcha_solver/solve.py --handout captcha-handout.zip --image captcha.png --engine template
py tools/captcha_solver/solve.py --handout captcha-handout.zip --image captcha.png --engine easyocr
```

## 원격 60라운드 실행

CTF 인스턴스 포트는 재시작 시 바뀔 수 있으므로 URL을 인자로 줍니다.

```powershell
py tools/captcha_solver/solve.py `
  --url http://3.35.97.192:13545/ `
  --handout captcha-handout.zip `
  --expected-len 6 `
  --target 60 `
  --headed
```

브라우저 창을 숨기려면 `--headed`를 빼면 됩니다.

### 자주 쓰는 옵션

```text
--engine hybrid|template|easyocr
--min-confidence 0.55
--captcha-path /captcha
--submit-path /submit
--debug-dir captcha_debug
```

OCR이 너무 자주 낮은 confidence로 중단되면 실제 CAPTCHA 샘플을 먼저 저장해서 `--image`로 template/easyocr 결과를 비교한 뒤 임계값을 조정하는 것이 좋습니다.

## 현재 검증 범위

- Python 문법 검증 완료
- 핸드아웃 ZIP에서 Roboto Mono 4종 자동 탐색/추출 확인
- `a-z0-9` 36문자 template 생성 확인
- 알려진 `/submit` 응답 구조와 60-streak 상태 처리 반영
- Playwright가 `/captcha` 원본 response를 가로채도록 구현

현재 CTF 인스턴스는 외부 검증 환경에서 `Connection refused` 상태였기 때문에 **60라운드 live E2E 성공까지는 아직 검증하지 못했습니다.** 실제 인스턴스에서 실패하면 `captcha_debug/`의 PNG/JSON을 기준으로 전처리와 confidence 기준을 조정하면 됩니다.
