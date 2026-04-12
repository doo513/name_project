import tkinter as tk
from tkinter import ttk, messagebox

from CORE import db


class StudyListWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("학습 리스트")
        self.win.geometry("920x560")
        self.win.minsize(700, 420)

        self._build_ui()
        self.load_data()

    def _build_ui(self) -> None:
        top = tk.Frame(self.win, padx=12, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="학습 리스트", font=("Segoe UI", 12, "bold")).pack(side="left")

        self.keyword_var = tk.StringVar()
        tk.Entry(top, textvariable=self.keyword_var, width=28).pack(side="right", padx=(8, 0))
        tk.Button(top, text="검색", width=10, command=self.search_data).pack(side="right", padx=(6, 0))
        tk.Button(top, text="새로고침", width=10, command=self.load_data).pack(side="right")

        columns = ("id", "created_at", "preview")
        self.tree = ttk.Treeview(self.win, columns=columns, show="headings")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.tree.heading("id", text="ID")
        self.tree.heading("created_at", text="저장 시각")
        self.tree.heading("preview", text="내용 미리보기")

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("created_at", width=180, anchor="center")
        self.tree.column("preview", width=620, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self.show_selected_detail)

        detail_frame = tk.LabelFrame(self.win, text="상세 내용", padx=8, pady=8)
        detail_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.detail = tk.Text(detail_frame, height=7, wrap="word", font=("Consolas", 10))
        self.detail.pack(fill="x")

        bottom = tk.Frame(self.win, padx=12, pady=(0, 12))
        bottom.pack(fill="x")

        tk.Button(bottom, text="선택 항목 삭제", width=14, command=self.delete_selected).pack(side="right")

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
            self.detail.insert("1.0", f"총 {len(rows)}건")
        except Exception as exc:
            messagebox.showerror("오류", f"목록 조회 실패\n{exc}")

    def search_data(self) -> None:
        keyword = self.keyword_var.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            rows = db.search_ocr_results(keyword)
            self._insert_rows(rows)
            self.detail.delete("1.0", "end")
            self.detail.insert("1.0", f"검색어 '{keyword}' 결과: {len(rows)}건")
        except Exception as exc:
            messagebox.showerror("오류", f"검색 실패\n{exc}")

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
                f"저장 시각: {item['created_at']}\n"
                f"영역: {item.get('source_region') or '-'}\n"
                f"태그: {item.get('tags') or '-'}\n\n"
                f"{item['content']}"
            )
            self.detail.delete("1.0", "end")
            self.detail.insert("1.0", text)
        except Exception as exc:
            messagebox.showerror("오류", f"상세 조회 실패\n{exc}")

    def delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("알림", "삭제할 항목을 선택해 주세요.")
            return
        row_id = int(selected[0])
        if not messagebox.askyesno("확인", f"ID {row_id} 항목을 삭제할까요?"):
            return
        try:
            ok = db.delete_ocr_result(row_id)
            if ok:
                self.load_data()
                messagebox.showinfo("완료", "삭제했습니다.")
            else:
                messagebox.showwarning("알림", "이미 삭제되었거나 항목이 없습니다.")
        except Exception as exc:
            messagebox.showerror("오류", f"삭제 실패\n{exc}")


def open_study_list_window(parent: tk.Misc) -> StudyListWindow:
    return StudyListWindow(parent)
