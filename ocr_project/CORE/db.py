import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ocr_study.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_region TEXT,
                tags TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_ocr_result(content: str, source_region: Optional[str] = None, tags: Optional[str] = None) -> int:
    if not content or not content.strip():
        raise ValueError("content is empty")

    init_db()
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ocr_results (content, source_region, tags, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (content.strip(), source_region, tags, created_at),
        )
        conn.commit()
        return int(cursor.lastrowid)


def save_study_item(content: str) -> int:
    return save_ocr_result(content=content)


def insert_ocr_result(content: str) -> int:
    return save_ocr_result(content=content)


def list_ocr_results(limit: int = 200) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, content, source_region, tags, created_at
            FROM ocr_results
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_ocr_result(result_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, content, source_region, tags, created_at
            FROM ocr_results
            WHERE id = ?
            """,
            (result_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_ocr_result(result_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM ocr_results WHERE id = ?", (result_id,))
        conn.commit()
        return cursor.rowcount > 0


def search_ocr_results(keyword: str, limit: int = 200) -> List[Dict[str, Any]]:
    init_db()
    q = f"%{keyword.strip()}%"
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, content, source_region, tags, created_at
            FROM ocr_results
            WHERE content LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, limit),
        ).fetchall()
    return [dict(row) for row in rows]


init_db()
