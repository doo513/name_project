import json
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
                payload_json TEXT,
                source_region TEXT,
                tags TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(ocr_results)").fetchall()
        }
        if "payload_json" not in existing_columns:
            conn.execute("ALTER TABLE ocr_results ADD COLUMN payload_json TEXT")
        conn.commit()


def save_ocr_result(
    content: str,
    source_region: Optional[str] = None,
    tags: Optional[str] = None,
    payload_json: Optional[str] = None,
    created_at: Optional[str] = None,
    translation: Optional[str] = None,
) -> int:
    if not content or not content.strip():
        raise ValueError("content is empty")

    init_db()
    created_at = created_at or datetime.now().isoformat(timespec="seconds")

    payload_data = {
        "time": created_at,
        "content": content.strip(),
    }
    if translation:
        payload_data["translation"] = translation.strip()
    payload_json = json.dumps(payload_data, ensure_ascii=False)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ocr_results (content, payload_json, source_region, tags, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (content.strip(), payload_json, source_region, tags, created_at),
        )
        conn.commit()
        return int(cursor.lastrowid)


def save_study_item(content: str) -> int:
    return save_ocr_result(content=content)


def insert_ocr_result(content: str) -> int:
    return save_ocr_result(content=content)


def save_json_record(content: str, source_region: Optional[str] = None, tags: Optional[str] = None, translation: Optional[str] = None) -> int:
    timestamp = datetime.now().isoformat(timespec="seconds")
    payload_data = {
        "time": timestamp,
        "content": content.strip(),
    }
    if translation:
        payload_data["translation"] = translation.strip()
    payload = json.dumps(payload_data, ensure_ascii=False)

    return save_ocr_result(
        content=content,
        payload_json=payload,
        source_region=source_region,
        tags=tags,
        created_at=timestamp,
        translation=translation,
    )


def list_ocr_results(limit: int = 200) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, content, payload_json, source_region, tags, created_at
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
            SELECT id, content, payload_json, source_region, tags, created_at
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
            SELECT id, content, payload_json, source_region, tags, created_at
            FROM ocr_results
            WHERE content LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, limit),
        ).fetchall()
    return [dict(row) for row in rows]


init_db()
