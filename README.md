# OCR OSS

Python `tkinter` desktop app for selecting a screen region, capturing it on an interval, and running OCR only when the image changes.

## How To Use

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Run

```bash
cd ocr_project
python main.py
```

### 3. Current Flow

1. Click `Open Region Selector`.
2. Drag to select the OCR region.
3. The `Capture OCR Panel` starts monitoring that area every 2 seconds.
4. OCR runs only when the captured image is different from the last frame, or when `Recognize Now` is pressed.
5. The panel shows only the latest OCR result. Results are not accumulated.
6. Click `Save` to store the current result in the local database.
7. Open `Study List` to review saved results.

## Current Development Status

### Implemented

- Region selection is separated from OCR execution.
- Capture and OCR responsibilities are split into separate modules.
- OCR runs after change detection instead of on every frame.
- Manual recognition is available from the capture panel.
- The app keeps only the latest OCR result in memory.
- OCR language selection is available as a 2-language pair.
- Save is user-driven and stores the current result to SQLite.
- Each saved record includes a JSON payload with `time` and `content`.

### Current Save Format

Saved OCR records keep plain text for list and search features, and also store a JSON payload in the database.

```json
{
  "time": "2026-04-15T14:30:00",
  "content": "recognized text"
}
```

## Current Structure

```text
ocr_project/
|- main.py
|- CORE/
|  |- db.py
|  |- ocr_engine.py
|  \- ocr_service.py
\- UI/
   |- capture_monitor.py
   |- selector.py
   |- study_list.py
   |- test_ui.py
   \- overlay.py
```

## Design Notes

- Screen capture is relatively cheap. OCR is the expensive step.
- The current design avoids repeated OCR by checking whether the frame changed first.
- Results are intentionally not accumulated. The user decides when the current OCR output should be saved.
- The current language model strategy is a simple 2-language pair chosen by the user.

## Known Limits

- OCR accuracy still depends heavily on ROI size, text size, contrast, and the selected language pair.
- Very wide regions are slower and usually less accurate than narrow, focused regions.
- `overlay.py` is still present in the repo, but the current main flow uses `capture_monitor.py` instead.

## Next Development Items

### Short Term

- Add OCR preprocessing such as upscale, grayscale, contrast, and threshold.
- Expose capture interval and more OCR options in the UI.
- Decide whether `overlay.py` should be removed entirely.
- Improve save metadata if region or language history becomes important.

### Mid Term

- Add separate subtitle mode and document mode.
- Compare OCR engines for better accuracy and memory usage.
- Improve saved-result filtering and study workflows.

### Long Term

- Explore translation and summary workflows on top of OCR output.
- Evaluate GPU or batch-oriented OCR if the app grows beyond small ROI capture.
