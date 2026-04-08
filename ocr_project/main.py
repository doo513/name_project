import tkinter as tk
from tkinter import messagebox


class MainApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OCR Integrated Study App")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        self.selected_region = None
        self.capture_path = None
        self.ocr_text = []

        self._build_ui()

    def _build_ui(self) -> None:
        tk.Label(self.root, text="Main Hub", font=("Segoe UI", 16, "bold")).pack(pady=(24, 8))
        tk.Label(
            self.root,
            text="Transparent overlay info + region capture flow",
            font=("Segoe UI", 10),
            fg="#555555",
        ).pack(pady=(0, 12))

        self.region_label_var = tk.StringVar(value="Selected Region: None")
        self.capture_label_var = tk.StringVar(value="Capture Path: None")

        tk.Label(self.root, textvariable=self.region_label_var, font=("Segoe UI", 9), fg="#444444").pack(pady=(0, 4))
        tk.Label(self.root, textvariable=self.capture_label_var, font=("Segoe UI", 9), fg="#444444", wraplength=460).pack(pady=(0, 12))

        btn_style = {
            "width": 30,
            "height": 2,
            "font": ("Segoe UI", 10),
            "bd": 0,
            "relief": "flat",
            "bg": "#2d6cdf",
            "fg": "white",
            "activebackground": "#2559b7",
            "activeforeground": "white",
            "cursor": "hand2",
        }

        tk.Button(self.root, text="Open Region Selector", command=self.open_selector, **btn_style).pack(pady=6)
        tk.Button(self.root, text="Open Overlay", command=self.open_overlay, **btn_style).pack(pady=6)
        tk.Button(self.root, text="Open Study List", command=self.open_study_list, **btn_style).pack(pady=6)
        tk.Button(self.root, text="Open Test UI", command=self.open_test_ui, **btn_style).pack(pady=6)

    def _on_region_selected(self, region, capture_path=None, ocr_text=None) -> None:
        self.selected_region = region
        self.capture_path = capture_path
        self.ocr_text = ocr_text or []
        
        self.region_label_var.set(f"Selected Region: {region}")
        self.capture_label_var.set(f"Capture Path: {capture_path or 'None'}")
        
        # Show OCR preview
        if self.ocr_text:
            preview = '\n'.join(self.ocr_text)
            truncated = preview[:100] + ('...' if len(preview) > 100 else '')
            self.capture_label_var.set(f"OCR: {truncated}")

    def open_selector(self) -> None:
        try:
            from UI.selector import open_selector_window

            open_selector_window(self.root, on_selected=self._on_region_selected)
        except ImportError:
            self._open_placeholder("Selector", "selector.py or open_selector_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open selector window.\n{exc}")

    def open_overlay(self) -> None:
        try:
            from UI.overlay import open_overlay_window

            # Use OCR text if available
            if self.ocr_text:
                initial_text = '\n'.join(self.ocr_text)
            else:
                initial_text = "OCR result preview\n\n- Non-intrusive transparent overlay"
            
            payload = {
                "initial_text": initial_text,
                "selected_region": self.selected_region,
                "capture_path": self.capture_path,
            }
            open_overlay_window(self.root, data=payload)
        except ImportError:
            self._open_placeholder("Overlay", "overlay.py or open_overlay_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open overlay window.\n{exc}")

    def open_study_list(self) -> None:
        try:
            from UI.study_list import open_study_list_window

            open_study_list_window(self.root)
        except ImportError:
            self._open_placeholder("Study List", "study_list.py or open_study_list_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open study list window.\n{exc}")

    def open_test_ui(self) -> None:
        try:
            from UI.test_ui import open_test_window

            open_test_window(self.root)
        except ImportError:
            self._open_placeholder("Test UI", "test_ui.py or open_test_window is missing.")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open test window.\n{exc}")

    def _open_placeholder(self, title: str, message: str) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("380x180")
        win.resizable(False, False)

        tk.Label(win, text=title, font=("Segoe UI", 13, "bold")).pack(pady=(20, 10))
        tk.Label(win, text=message, font=("Segoe UI", 10), fg="#444444", wraplength=330).pack(pady=(0, 16))
        tk.Button(win, text="Close", command=win.destroy, width=12).pack()


def main() -> None:
    root = tk.Tk()
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
