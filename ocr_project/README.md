# ocr_project

Desktop OCR study app built with Python and `tkinter`.

## Usage

1. Run `python main.py`
2. Click `Open Region Selector`
3. Drag to select the capture region
4. Check the latest OCR result in `Capture OCR Panel`
5. Press `Recognize Now` for manual OCR
6. Press `Save` to store the current result in the database

## Current Structure

```text
main.py
|- UI.selector            # region selection overlay
|- UI.capture_monitor     # periodic capture panel and result display
|- CORE.ocr_service       # image to OCR text
|- CORE.db                # local database save and query
|- UI.study_list          # saved results list
\- UI.test_ui             # review / test UI
```

## Current Status

### Working

- Drag-based region selection
- 2-second periodic region capture
- Change detection before OCR
- User-selectable 2-language OCR pair
- Manual recognition button
- User-triggered save flow
- JSON payload save inside SQLite

### Not Finished Yet

- OCR preprocessing is still minimal
- Wide regions are not optimized for speed
- OCR accuracy tuning is still needed
- `overlay.py` remains in the codebase but is no longer the main output path

## Saved Data

Each saved result currently stores JSON payload data like this:

```json
{
  "time": "2026-04-15T14:30:00",
  "content": "recognized text"
}
```

## Next Steps

- Add OCR preprocessing options
- Improve capture interval and OCR settings UI
- Compare OCR engines if EasyOCR remains too heavy
- Refine the save / study workflow
