import json
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
        top = tk.Frame(self.win, padx=12, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Study List", font=("Segoe UI", 12, "bold")).pack(side="left")

        self.keyword_var = tk.StringVar()
        tk.Entry(top, textvariable=self.keyword_var, width=28).pack(side="right", padx=(8, 0))
        tk.Button(top, text="Search", width=10, command=self.search_data).pack(side="right", padx=(6, 0))
        tk.Button(top, text="Refresh", width=10, command=self.load_data).pack(side="right")

        columns = ("id", "created_at", "preview")
        self.tree = ttk.Treeview(self.win, columns=columns, show="headings")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.tree.heading("id", text="ID")
        self.tree.heading("created_at", text="Saved At")
        self.tree.heading("preview", text="Preview")

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("created_at", width=180, anchor="center")
        self.tree.column("preview", width=620, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self.show_selected_detail)

        detail_frame = tk.LabelFrame(self.win, text="Details", padx=8, pady=8)
        detail_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.detail = tk.Text(detail_frame, height=7, wrap="word", font=("Consolas", 10))
        self.detail.pack(fill="x")

        bottom = tk.Frame(self.win, padx=12, pady=(0, 12))
        bottom.pack(fill="x")

        tk.Button(bottom, text="Delete Selected", width=14, command=self.delete_selected).pack(side="right")

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

            payload = item.get("payload_json")
            json_block = ""
            if payload:
                try:
                    parsed = json.loads(payload)
                    json_block = "\n\nJSON Payload:\n" + json.dumps(parsed, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    json_block = f"\n\nJSON Payload:\n{payload}"

            text = (
                f"ID: {item['id']}\n"
                f"Saved At: {item['created_at']}\n"
                f"Region: {item.get('source_region') or '-'}\n"
                f"Tags: {item.get('tags') or '-'}\n\n"
                f"{item['content']}"
                f"{json_block}"
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
