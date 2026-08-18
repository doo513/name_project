#!/usr/bin/env python3
"""CTF CAPTCHA solver for the browser challenge observed in August 2026.

The challenge frontend owns /start, authHeaders(), token, and round_nonce.
This tool deliberately leaves those values inside the browser. It intercepts
only the real /captcha image response, recognizes the six-character answer,
fills the page's answer input, and lets the site's own submit handler send:

    {"token": ..., "answer": ..., "round_nonce": ...}

The /submit JSON response is used as the source of truth for streak/target.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import string
import time
import zipfile
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Iterable, Optional
from urllib.parse import urlparse

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CHARSET = string.ascii_lowercase + string.digits
FONT_NAMES = (
    "RobotoMono-Bold.ttf",
    "RobotoMono-BoldItalic.ttf",
    "RobotoMono-Medium.ttf",
    "RobotoMono-MediumItalic.ttf",
)
FLAG_RE = re.compile(r"[A-Za-z0-9_]{2,32}\{[^}\r\n]{4,256}\}")


@dataclass(frozen=True)
class Candidate:
    text: str
    confidence: float
    engine: str
    detail: str = ""


def _sanitize(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch in CHARSET)


def _decode_gray(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("/captcha response is not a decodable raster image")
    return image


def _threshold(gray: np.ndarray) -> np.ndarray:
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask


def _prepare_text_mask(gray: np.ndarray) -> np.ndarray:
    """Suppress thin interference lines while preserving thicker glyph strokes."""
    raw = _threshold(gray)
    distance = cv2.distanceTransform(raw, cv2.DIST_L2, 5)
    core = (distance > 1.05).astype(np.uint8) * 255
    restored = cv2.dilate(core, np.ones((3, 3), np.uint8), iterations=1)

    if cv2.countNonZero(restored) < 30:
        restored = raw

    # Thin decorative lines can extend across almost the full 240px image.
    # After the thickness filter, the actual text normally forms the dominant
    # component. Use its bbox to reject remote line fragments, but preserve all
    # reconstructed pixels inside the bbox so detached i/j dots are not lost.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(restored, 8)
    if n <= 1:
        return restored

    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = stats[idx]
    if area < 20:
        return restored

    pad_x = max(4, int(round(w * 0.05)))
    pad_y = max(4, int(round(h * 0.18)))
    x1, x2 = max(0, x - pad_x), min(restored.shape[1], x + w + pad_x)
    y1, y2 = max(0, y - pad_y), min(restored.shape[0], y + h + pad_y)
    return restored[y1:y2, x1:x2]


def _crop_foreground(mask: np.ndarray) -> np.ndarray:
    points = cv2.findNonZero(mask)
    if points is None:
        return np.zeros((8, 8), dtype=np.uint8)
    x, y, w, h = cv2.boundingRect(points)
    return mask[y : y + h, x : x + w]


def _normalize(mask: np.ndarray, width: int = 48, height: int = 64) -> np.ndarray:
    mask = _crop_foreground(mask)
    h, w = mask.shape
    if h <= 0 or w <= 0:
        return np.zeros((height, width), dtype=np.uint8)

    scale = min((width - 8) / w, (height - 8) / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_AREA)
    _, resized = cv2.threshold(resized, 96, 255, cv2.THRESH_BINARY)

    out = np.zeros((height, width), dtype=np.uint8)
    ox = (width - nw) // 2
    oy = (height - nh) // 2
    out[oy : oy + nh, ox : ox + nw] = resized
    return out


def _segment(mask: np.ndarray, count: int) -> list[np.ndarray]:
    """Segment a fixed-width font CAPTCHA using projection minima."""
    h, w = mask.shape
    projection = (mask > 0).sum(axis=0).astype(np.float32)
    if w >= 5:
        projection = np.convolve(projection, np.ones(5, np.float32) / 5.0, mode="same")

    active_threshold = max(2.0, h * 0.055)
    active = np.flatnonzero(projection >= active_threshold)
    if len(active) >= count * 2:
        left, right = int(active[0]), int(active[-1] + 1)
    else:
        left, right = int(w * 0.03), int(w * 0.97)

    span = max(count, right - left)
    nominal = span / count
    cuts = [left]
    for i in range(1, count):
        expected = left + i * nominal
        radius = max(2, int(round(nominal * 0.28)))
        lo = max(cuts[-1] + 2, int(expected - radius))
        hi = min(right - 2, int(expected + radius))
        if lo >= hi:
            cut = int(round(expected))
        else:
            cut = lo + int(np.argmin(projection[lo : hi + 1]))
        cuts.append(cut)
    cuts.append(right)

    pad = max(1, int(round(nominal * 0.08)))
    return [
        mask[:, max(0, a - pad) : min(w, b + pad)]
        for a, b in zip(cuts, cuts[1:])
    ]


def _find_fonts(handout: Path, cache_dir: Path) -> list[Path]:
    if handout.is_dir():
        paths = [handout / "fonts" / name for name in FONT_NAMES]
        if not all(path.is_file() for path in paths):
            paths = [handout / name for name in FONT_NAMES]
        if all(path.is_file() for path in paths):
            return paths

    if handout.is_file() and handout.suffix.lower() == ".zip":
        cache_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(handout) as archive:
            members = {Path(name).name: name for name in archive.namelist()}
            missing = [name for name in FONT_NAMES if name not in members]
            if missing:
                raise FileNotFoundError(f"handout is missing fonts: {', '.join(missing)}")

            paths = []
            for name in FONT_NAMES:
                destination = cache_dir / name
                if not destination.exists():
                    destination.write_bytes(archive.read(members[name]))
                paths.append(destination)
            return paths

    raise FileNotFoundError(
        f"Challenge fonts were not found in {handout}. "
        "Pass --handout captcha-handout.zip or its extracted directory."
    )


def _render_template(ch: str, font_path: Path, size: int, angle: float) -> np.ndarray:
    font = ImageFont.truetype(str(font_path), size)
    canvas = Image.new("L", (140, 140), 255)
    draw = ImageDraw.Draw(canvas)
    box = draw.textbbox((0, 0), ch, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(
        ((140 - tw) // 2 - box[0], (140 - th) // 2 - box[1]),
        ch,
        font=font,
        fill=0,
    )
    if angle:
        canvas = canvas.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=255,
        )
    return _normalize(_threshold(np.asarray(canvas)))


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    aa, bb = a > 0, b > 0
    union = np.logical_or(aa, bb).sum()
    if not union:
        return 0.0
    return float(np.logical_and(aa, bb).sum() / union)


def _chamfer(a: np.ndarray, b: np.ndarray) -> float:
    aa = (a > 0).astype(np.uint8)
    bb = (b > 0).astype(np.uint8)
    if not aa.any() or not bb.any():
        return 0.0
    da = cv2.distanceTransform(1 - aa, cv2.DIST_L2, 3)
    db = cv2.distanceTransform(1 - bb, cv2.DIST_L2, 3)
    d1 = float(da[bb.astype(bool)].mean())
    d2 = float(db[aa.astype(bool)].mean())
    return math.exp(-(d1 + d2) / 5.6)


class TemplateRecognizer:
    """Recognizer that uses the exact four fonts shipped with the handout."""

    def __init__(self, fonts: Iterable[Path]):
        self.templates: dict[str, list[np.ndarray]] = {ch: [] for ch in CHARSET}
        for ch in CHARSET:
            for font_path in fonts:
                for size in (46, 58, 70):
                    for angle in (-8.0, -4.0, 0.0, 4.0, 8.0):
                        self.templates[ch].append(_render_template(ch, font_path, size, angle))

    @staticmethod
    def _score(target: np.ndarray, template: np.ndarray) -> float:
        return 0.35 * _iou(target, template) + 0.65 * _chamfer(target, template)

    def solve(self, image_bytes: bytes, expected_len: int) -> Candidate:
        gray = _decode_gray(image_bytes)
        mask = _prepare_text_mask(gray)
        parts = _segment(mask, expected_len)
        answer: list[str] = []
        scores: list[float] = []

        for part in parts:
            target = _normalize(part)
            best_ch, best_score = "?", -1.0
            for ch, variants in self.templates.items():
                score = max(self._score(target, variant) for variant in variants)
                if score > best_score:
                    best_ch, best_score = ch, score
            answer.append(best_ch)
            scores.append(best_score)

        confidence = min(scores) if scores else 0.0
        return Candidate(
            text="".join(answer),
            confidence=confidence,
            engine="template",
            detail="per-char=" + ",".join(f"{score:.3f}" for score in scores),
        )


class EasyOCRRecognizer:
    """Full-string OCR backend using the repository's existing EasyOCR stack."""

    def __init__(self):
        try:
            import easyocr
        except ImportError as exc:
            raise RuntimeError("EasyOCR is not installed") from exc
        self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def _variants(self, image_bytes: bytes) -> list[np.ndarray]:
        gray = _decode_gray(image_bytes)
        prepared = _prepare_text_mask(gray)
        cleaned = 255 - prepared
        return [
            gray,
            cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC),
            cleaned,
            cv2.resize(cleaned, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_NEAREST),
        ]

    def solve(self, image_bytes: bytes, expected_len: int) -> Optional[Candidate]:
        votes: list[tuple[str, float]] = []
        for variant in self._variants(image_bytes):
            try:
                result = self.reader.readtext(
                    variant,
                    detail=1,
                    paragraph=False,
                    allowlist=CHARSET,
                    decoder="greedy",
                    text_threshold=0.25,
                    low_text=0.20,
                    link_threshold=0.20,
                    width_ths=2.0,
                )
            except Exception:
                continue

            ordered = sorted(result, key=lambda item: min(point[0] for point in item[0]))
            text = _sanitize("".join(item[1] for item in ordered))
            if len(text) != expected_len:
                continue
            confidence = float(np.mean([float(item[2]) for item in ordered])) if ordered else 0.0
            votes.append((text, confidence))

        if not votes:
            return None

        counts = Counter(text for text, _ in votes)
        best_text, vote_count = max(
            counts.items(),
            key=lambda item: (item[1], max(score for text, score in votes if text == item[0])),
        )
        best_conf = max(score for text, score in votes if text == best_text)
        confidence = min(1.0, best_conf + 0.08 * (vote_count - 1))
        return Candidate(best_text, confidence, "easyocr", f"votes={vote_count}/{len(votes)}")


class HybridRecognizer:
    def __init__(self, template: TemplateRecognizer, use_easyocr: bool):
        self.template = template
        self.easyocr: Optional[EasyOCRRecognizer] = None
        if use_easyocr:
            try:
                self.easyocr = EasyOCRRecognizer()
            except Exception as exc:
                print(f"[!] EasyOCR unavailable, template-only mode: {exc}")

    def solve(self, image_bytes: bytes, expected_len: int, engine: str) -> tuple[Candidate, list[Candidate]]:
        candidates: list[Candidate] = []
        template = self.template.solve(image_bytes, expected_len)
        candidates.append(template)

        easy = None
        if self.easyocr is not None and engine in ("easyocr", "hybrid"):
            easy = self.easyocr.solve(image_bytes, expected_len)
            if easy is not None:
                candidates.append(easy)

        if engine == "template":
            return template, candidates
        if engine == "easyocr":
            if easy is None:
                raise RuntimeError("EasyOCR did not produce an exact-length answer")
            return easy, candidates

        if easy is not None and easy.text == template.text:
            return Candidate(
                easy.text,
                max(easy.confidence, template.confidence),
                "hybrid",
                "template/easyocr agreement",
            ), candidates

        if easy is not None and easy.confidence >= 0.82:
            return easy, candidates
        return template, candidates


class ChallengeBrowser:
    """Use the challenge's own JS as the protocol/authentication client."""

    def __init__(self, page, captcha_path: str, submit_path: str):
        self.page = page
        self.captcha_path = captcha_path
        self.submit_path = submit_path
        self.captchas: Deque[bytes] = deque()
        self.results: Deque[dict] = deque()
        page.on("response", self._on_response)

    def _on_response(self, response) -> None:
        try:
            path = urlparse(response.url).path
            if path == self.captcha_path and response.ok:
                body = response.body()
                ctype = (response.headers.get("content-type") or "").lower()
                if ctype.startswith("image/") or body.startswith((b"\x89PNG", b"\xff\xd8")):
                    self.captchas.append(body)
            elif path == self.submit_path:
                try:
                    payload = response.json()
                except Exception:
                    payload = {"status": response.status, "body": response.text()}
                if isinstance(payload, dict):
                    self.results.append(payload)
        except Exception:
            return

    def _wait(self, queue: Deque, timeout_ms: int, label: str):
        deadline = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < deadline:
            if queue:
                return queue.popleft()
            self.page.wait_for_timeout(50)
        raise TimeoutError(f"timed out waiting for {label}")

    def wait_captcha(self, timeout_ms: int = 8000) -> bytes:
        while len(self.captchas) > 1:
            self.captchas.popleft()
        return self._wait(self.captchas, timeout_ms, "/captcha")

    def wait_result(self, timeout_ms: int = 8000) -> dict:
        return self._wait(self.results, timeout_ms, "/submit")

    def click_start(self) -> bool:
        selectors = (
            "#startButton",
            "button[data-action='start']",
            "button:has-text('Start')",
            "button:has-text('시작')",
        )
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                if locator.count() and locator.first.is_visible() and locator.first.is_enabled():
                    locator.first.click()
                    return True
            except Exception:
                continue
        return False

    def _answer_input(self):
        selectors = (
            "#answer",
            "input[name='answer']",
            "input[id*='answer' i]",
            "input[name*='answer' i]",
            "input[name*='captcha' i]",
            "input[type='text']",
        )
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                for idx in range(locator.count()):
                    item = locator.nth(idx)
                    if item.is_visible() and item.is_enabled():
                        return item
            except Exception:
                continue
        raise RuntimeError("could not find the CAPTCHA answer input")

    def submit(self, answer: str) -> None:
        field = self._answer_input()
        field.fill(answer.lower())
        field.press("Enter")


def _extract_flag(value) -> Optional[str]:
    if isinstance(value, dict):
        for item in value.values():
            found = _extract_flag(item)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_flag(item)
            if found:
                return found
    elif isinstance(value, str):
        match = FLAG_RE.search(value)
        if match:
            return match.group(0)
    return None


def _save_debug(
    directory: Path,
    round_no: int,
    image: bytes,
    chosen: Candidate,
    candidates: list[Candidate],
    result: Optional[dict] = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"captcha_{round_no:03d}_{chosen.text}.png").write_bytes(image)
    metadata = {
        "chosen": chosen.__dict__,
        "candidates": [candidate.__dict__ for candidate in candidates],
        "result": result,
    }
    (directory / f"round_{round_no:03d}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _resolve_handout(value: str, script_dir: Path) -> Path:
    requested = Path(value)
    if requested.is_absolute():
        return requested
    candidates = (
        Path.cwd() / requested,
        script_dir / requested,
        script_dir.parent.parent / requested,
    )
    return next((path for path in candidates if path.exists()), candidates[0])


def _recognize_file(path: Path, recognizer: HybridRecognizer, expected_len: int, engine: str) -> int:
    image = path.read_bytes()
    chosen, candidates = recognizer.solve(image, expected_len, engine)
    for candidate in candidates:
        print(
            f"[{candidate.engine}] {candidate.text} "
            f"confidence={candidate.confidence:.3f} {candidate.detail}"
        )
    print(f"[chosen] {chosen.text} ({chosen.engine}, {chosen.confidence:.3f})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="60-streak Roboto Mono CAPTCHA solver")
    parser.add_argument("--url", help="challenge URL, e.g. http://3.35.97.192:13545/")
    parser.add_argument("--handout", default="captcha-handout.zip")
    parser.add_argument("--expected-len", type=int, default=6)
    parser.add_argument("--target", type=int, default=60)
    parser.add_argument("--engine", choices=("template", "easyocr", "hybrid"), default="hybrid")
    parser.add_argument("--captcha-path", default="/captcha")
    parser.add_argument("--submit-path", default="/submit")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--debug-dir", default="captcha_debug")
    parser.add_argument("--image", help="recognize one local CAPTCHA PNG and exit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    script_dir = Path(__file__).resolve().parent
    handout = _resolve_handout(args.handout, script_dir)
    fonts = _find_fonts(handout, script_dir / ".fonts_cache")

    print("[*] challenge fonts")
    for path in fonts:
        print(f"    {path}")
    print("[*] building exact-font templates (a-z0-9) ...")
    template = TemplateRecognizer(fonts)
    recognizer = HybridRecognizer(template, use_easyocr=args.engine in ("easyocr", "hybrid"))
    print("[+] recognizer ready")

    if args.image:
        return _recognize_file(Path(args.image), recognizer, args.expected_len, args.engine)

    if not args.url:
        print("[!] --url is required unless --image is used")
        return 2

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright is not installed")
        print("    py -m pip install -r tools/captcha_solver/requirements.txt")
        print("    py -m playwright install chromium")
        return 3

    debug_dir = Path(args.debug_dir)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        challenge = ChallengeBrowser(page, args.captcha_path, args.submit_path)

        print(f"[*] opening {args.url}")
        page.goto(args.url, wait_until="domcontentloaded", timeout=15_000)

        try:
            image = challenge.wait_captcha(timeout_ms=2_000)
        except TimeoutError:
            if not challenge.click_start():
                print("[!] no /captcha response and no Start button was found")
                browser.close()
                return 4
            image = challenge.wait_captcha(timeout_ms=8_000)

        for round_no in range(1, args.target + 1):
            chosen, candidates = recognizer.solve(image, args.expected_len, args.engine)
            print(f"[{round_no:02d}/{args.target}] candidates:")
            for candidate in candidates:
                print(
                    f"    {candidate.engine:8s} {candidate.text} "
                    f"conf={candidate.confidence:.3f} {candidate.detail}"
                )
            print(f"    -> {chosen.text} via {chosen.engine}")

            if len(chosen.text) != args.expected_len or chosen.confidence < args.min_confidence:
                _save_debug(debug_dir, round_no, image, chosen, candidates)
                print(
                    f"[!] refusing to submit: confidence={chosen.confidence:.3f}, "
                    f"required={args.min_confidence:.3f}. Debug sample saved to {debug_dir}."
                )
                browser.close()
                return 5

            challenge.submit(chosen.text)
            result = challenge.wait_result()
            print(f"    submit={json.dumps(result, ensure_ascii=False)}")

            if not result.get("correct", False):
                _save_debug(debug_dir, round_no, image, chosen, candidates, result)
                print("[!] wrong answer; server did not preserve the streak")
                browser.close()
                return 6

            flag = _extract_flag(result)
            if flag:
                print(f"[FLAG] {flag}")
                browser.close()
                return 0

            streak = int(result.get("streak", round_no))
            target = int(result.get("target", args.target))
            qualified = bool(result.get("qualified", False))
            solved = bool(result.get("solved", False))
            print(f"    streak={streak}/{target} qualified={qualified} solved={solved}")

            if solved or streak >= target:
                page.wait_for_timeout(500)
                body = page.locator("body").inner_text() if page.locator("body").count() else ""
                flag = _extract_flag(body)
                if flag:
                    print(f"[FLAG] {flag}")
                else:
                    print("[+] target reached")
                    print(body[-3000:])
                browser.close()
                return 0

            image = challenge.wait_captcha(timeout_ms=8_000)

        browser.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
