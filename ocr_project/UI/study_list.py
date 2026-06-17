import tkinter as tk
from tkinter import messagebox, ttk

from CORE import db


class StudyListWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("Study List")
        self.win.geometry("920x560")
        self.win.minsize(700, 420)

        self._build_ui()
        self.load_data()

    def _build_ui(self) -> None:
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_rowconfigure(1, weight=1)
        self.win.grid_rowconfigure(2, weight=1)

        # Top toolbar
        top = tk.Frame(self.win, padx=12, pady=10)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        tk.Label(top, text="Study List", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")

        self.keyword_var = tk.StringVar()
        tk.Entry(top, textvariable=self.keyword_var, width=28).grid(row=0, column=1, sticky="e", padx=(8, 0))
        tk.Button(top, text="Search", width=10, command=self.search_data).grid(row=0, column=2, padx=(6, 0))
        tk.Button(top, text="Refresh", width=10, command=self.load_data).grid(row=0, column=3)

        # Treeview with scrollbar in a frame
        tree_frame = tk.Frame(self.win)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        columns = ("id", "created_at", "preview")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.heading("id", text="ID")
        self.tree.heading("created_at", text="Saved At")
        self.tree.heading("preview", text="Preview")

        self.tree.column("id", width=80, anchor="center", minwidth=60)
        self.tree.column("created_at", width=180, anchor="center", minwidth=140)
        self.tree.column("preview", width=620, anchor="w", minwidth=200)

        self.tree.bind("<<TreeviewSelect>>", self.show_selected_detail)

        # Detail frame - expandable
        detail_frame = tk.LabelFrame(self.win, text="Details", padx=8, pady=8)
        detail_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=10)
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(0, weight=1)

        self.detail = tk.Text(detail_frame, wrap="word", font=("Consolas", 10))
        self.detail.grid(row=0, column=0, sticky="nsew")

        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail.yview)
        detail_scroll.grid(row=0, column=1, sticky="ns")
        self.detail.configure(yscrollcommand=detail_scroll.set)

        # Bottom buttons
        bottom = tk.Frame(self.win, padx=12)
        bottom.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)

        tk.Button(bottom, text="Delete Selected", width=14, command=self.delete_selected).grid(row=0, column=1, sticky="e")

    def _preview(self, text: str, limit: int = 70) -> str:
        text = (text or "").replace("\n", " ").strip()
        return text if len(text) <= limit else text[: limit - 3] + "..."

    def _insert_rows(self, rows) -> None:
        self.tree.delete(*self.tree.get_children())
        for item in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["id"], item["created_at"], self._preview(item["content"])),
            )

    def load_data(self) -> None:
        try:
            rows = db.list_ocr_results()
            self._insert_rows(rows)
            self.detail.delete("1.0", "end")
            self.detail.insert("1.0", f"Total {len(rows)} item(s)")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load study list.\n{exc}")

    def search_data(self) -> None:
        keyword = self.keyword_var.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            rows = db.search_ocr_results(keyword)
            self._insert_rows(rows)
            self.detail.delete("1.0", "end")
            self.detail.insert("1.0", f"Search '{keyword}': {len(rows)} item(s)")
        except Exception as exc:
            messagebox.showerror("Error", f"Search failed.\n{exc}")

    def show_selected_detail(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        row_id = int(selected[0])
        try:
            item = db.get_ocr_result(row_id)
            if not item:
                return

            text = (
                f"ID: {item['id']}\n"
                f"Saved At: {item['created_at']}\n"
                f"Source Language: {item.get('source_language') or '-'}\n"
                f"Target Language: {item.get('target_language') or '-'}\n"
                f"Region: {item.get('source_region') or '-'}\n"
                f"Tags: {item.get('tags') or '-'}\n\n"
                f"OCR Text:\n{item['content']}\n\n"
                f"Translation:\n{item.get('translation_text') or '-'}"
            )
            self.detail.delete("1.0", "end")
            self.detail.insert("1.0", text)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load details.\n{exc}")

    def delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Notice", "Select an item to delete.")
            return

        row_id = int(selected[0])
        if not messagebox.askyesno("Confirm", f"Delete item ID {row_id}?"):
            return

        try:
            ok = db.delete_ocr_result(row_id)
            if ok:
                self.load_data()
                messagebox.showinfo("Done", "Deleted.")
            else:
                messagebox.showwarning("Notice", "Item was already removed or does not exist.")
        except Exception as exc:
            messagebox.showerror("Error", f"Delete failed.\n{exc}")


def open_study_list_window(parent: tk.Misc) -> StudyListWindow:
    return StudyListWindow(parent)
