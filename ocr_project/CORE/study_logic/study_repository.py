import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..db import DB_PATH, init_db


class StudyRepository:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = str(db_path or DB_PATH)
        init_db()
        self.ensure_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS study_problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_result_id INTEGER NOT NULL,
                    problem_type TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    source_text TEXT,
                    answer_text TEXT NOT NULL,
                    acceptable_answers_json TEXT NOT NULL DEFAULT '[]',
                    keyword_rules_json TEXT NOT NULL DEFAULT '{}',
                    difficulty TEXT NOT NULL DEFAULT 'medium',
                    hint_text TEXT,
                    explanation_text TEXT,
                    choice_options_json TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS study_problem_acceptable_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    answer_text TEXT NOT NULL,
                    normalized_answer TEXT NOT NULL,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (problem_id) REFERENCES study_problems(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS study_problem_keyword_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    rule_type TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (problem_id) REFERENCES study_problems(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS study_problem_choice_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL,
                    option_text TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (problem_id) REFERENCES study_problems(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS study_attempt_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_result_id INTEGER,
                    total_problems INTEGER NOT NULL DEFAULT 0,
                    solved_count INTEGER NOT NULL DEFAULT 0,
                    correct_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS study_attempt_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    problem_id INTEGER NOT NULL,
                    user_answer TEXT NOT NULL,
                    normalized_answer TEXT,
                    direct_status TEXT NOT NULL,
                    direct_score INTEGER NOT NULL,
                    ambiguity_reason TEXT,
                    gemini_used INTEGER NOT NULL DEFAULT 0,
                    gemini_feedback TEXT,
                    gemini_confidence INTEGER,
                    final_status TEXT NOT NULL,
                    final_score INTEGER NOT NULL,
                    judged_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES study_attempt_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (problem_id) REFERENCES study_problems(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS study_wrong_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id INTEGER NOT NULL UNIQUE,
                    wrong_count INTEGER NOT NULL DEFAULT 0,
                    last_session_id INTEGER,
                    last_record_id INTEGER,
                    last_user_answer TEXT,
                    is_resolved INTEGER NOT NULL DEFAULT 0,
                    first_wrong_at TEXT NOT NULL,
                    last_wrong_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (problem_id) REFERENCES study_problems(id) ON DELETE CASCADE,
                    FOREIGN KEY (last_session_id) REFERENCES study_attempt_sessions(id) ON DELETE SET NULL,
                    FOREIGN KEY (last_record_id) REFERENCES study_attempt_records(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_study_problems_ocr_result ON study_problems(ocr_result_id);
                CREATE INDEX IF NOT EXISTS idx_study_problems_type ON study_problems(problem_type);
                CREATE INDEX IF NOT EXISTS idx_study_problems_status ON study_problems(status);
                CREATE INDEX IF NOT EXISTS idx_study_answers_problem ON study_problem_acceptable_answers(problem_id);
                CREATE INDEX IF NOT EXISTS idx_study_keywords_problem ON study_problem_keyword_rules(problem_id);
                CREATE INDEX IF NOT EXISTS idx_study_options_problem ON study_problem_choice_options(problem_id);
                CREATE INDEX IF NOT EXISTS idx_study_sessions_ocr_result ON study_attempt_sessions(ocr_result_id);
                CREATE INDEX IF NOT EXISTS idx_study_sessions_status ON study_attempt_sessions(status);
                CREATE INDEX IF NOT EXISTS idx_study_records_session ON study_attempt_records(session_id);
                CREATE INDEX IF NOT EXISTS idx_study_records_problem ON study_attempt_records(problem_id);
                CREATE INDEX IF NOT EXISTS idx_study_records_final_status ON study_attempt_records(final_status);
                CREATE INDEX IF NOT EXISTS idx_study_wrong_resolved ON study_wrong_answers(is_resolved, updated_at DESC);
                """
            )
            existing_record_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(study_attempt_records)").fetchall()
            }
            if "gemini_feedback" not in existing_record_columns:
                conn.execute("ALTER TABLE study_attempt_records ADD COLUMN gemini_feedback TEXT")
            if "gemini_confidence" not in existing_record_columns:
                conn.execute("ALTER TABLE study_attempt_records ADD COLUMN gemini_confidence INTEGER")
            conn.commit()

    def normalize_answer(self, text: str) -> str:
        return " ".join((text or "").strip().casefold().split())

    def create_problem(
        self,
        *,
        ocr_result_id: int,
        problem_type: str,
        question_text: str,
        source_text: str,
        answer_text: str,
        acceptable_answers: List[str],
        keyword_rules: Dict[str, Any],
        difficulty: str,
        hint_text: Optional[str],
        explanation_text: Optional[str],
        choice_options: Optional[List[str]],
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO study_problems (
                    ocr_result_id, problem_type, question_text, source_text,
                    answer_text, difficulty, hint_text, explanation_text,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ocr_result_id,
                    problem_type,
                    question_text,
                    source_text,
                    answer_text,
                    difficulty,
                    hint_text,
                    explanation_text,
                    now,
                    now,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("failed to create study problem")
            problem_id = int(cursor.lastrowid)
            answers = acceptable_answers or [answer_text]
            for position, accepted_answer in enumerate(answers):
                conn.execute(
                    """
                    INSERT INTO study_problem_acceptable_answers (
                        problem_id, answer_text, normalized_answer, is_primary, position
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        problem_id,
                        accepted_answer,
                        self.normalize_answer(accepted_answer),
                        1 if position == 0 else 0,
                        position,
                    ),
                )
            for rule_type, keywords in (keyword_rules or {}).items():
                if not isinstance(keywords, list):
                    continue
                for position, keyword in enumerate(keywords):
                    conn.execute(
                        """
                        INSERT INTO study_problem_keyword_rules (
                            problem_id, rule_type, keyword, position
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (problem_id, str(rule_type), str(keyword), position),
                    )
            for position, option in enumerate(choice_options or []):
                conn.execute(
                    """
                    INSERT INTO study_problem_choice_options (problem_id, option_text, position)
                    VALUES (?, ?, ?)
                    """,
                    (problem_id, option, position),
                )
            conn.commit()
            return problem_id

    def list_problems_for_ocr_result(self, ocr_result_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM study_problems
                WHERE ocr_result_id = ? AND status = 'active'
                ORDER BY id ASC
                """,
                (ocr_result_id,),
            ).fetchall()
        return [self._hydrate_problem(dict(row)) for row in rows]

    def get_problem(self, problem_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM study_problems WHERE id = ?",
                (problem_id,),
            ).fetchone()
        return self._hydrate_problem(dict(row)) if row else None

    def _hydrate_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        problem_id = int(problem["id"])
        with self.get_connection() as conn:
            answer_rows = conn.execute(
                """
                SELECT answer_text
                FROM study_problem_acceptable_answers
                WHERE problem_id = ?
                ORDER BY position ASC, id ASC
                """,
                (problem_id,),
            ).fetchall()
            keyword_rows = conn.execute(
                """
                SELECT rule_type, keyword
                FROM study_problem_keyword_rules
                WHERE problem_id = ?
                ORDER BY rule_type ASC, position ASC, id ASC
                """,
                (problem_id,),
            ).fetchall()
            option_rows = conn.execute(
                """
                SELECT option_text
                FROM study_problem_choice_options
                WHERE problem_id = ?
                ORDER BY position ASC, id ASC
                """,
                (problem_id,),
            ).fetchall()
        acceptable_answers = [row["answer_text"] for row in answer_rows] or [problem.get("answer_text", "")]
        keyword_rules: Dict[str, List[str]] = {}
        for row in keyword_rows:
            keyword_rules.setdefault(row["rule_type"], []).append(row["keyword"])
        problem["acceptable_answers"] = acceptable_answers
        problem["keyword_rules"] = keyword_rules
        problem["choice_options"] = [row["option_text"] for row in option_rows]
        return problem

    def start_attempt_session(self, ocr_result_id: Optional[int], total_problems: int) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO study_attempt_sessions (
                    ocr_result_id, total_problems, started_at
                ) VALUES (?, ?, ?)
                """,
                (ocr_result_id, total_problems, now),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("failed to start attempt session")
            return int(cursor.lastrowid)

    def record_attempt(
        self,
        *,
        session_id: int,
        problem_id: int,
        user_answer: str,
        normalized_answer: str,
        direct_status: str,
        direct_score: int,
        ambiguity_reason: Optional[str],
        gemini_used: bool,
        final_status: str,
        final_score: int,
        judged_by: str,
        gemini_feedback: Optional[str] = None,
        gemini_confidence: Optional[int] = None,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO study_attempt_records (
                    session_id, problem_id, user_answer, normalized_answer,
                    direct_status, direct_score, ambiguity_reason,
                    gemini_used, gemini_feedback, gemini_confidence, final_status,
                    final_score, judged_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    problem_id,
                    user_answer,
                    normalized_answer,
                    direct_status,
                    direct_score,
                    ambiguity_reason,
                    1 if gemini_used else 0,
                    gemini_feedback,
                    gemini_confidence,
                    final_status,
                    final_score,
                    judged_by,
                    now,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("failed to record attempt")
            record_id = int(cursor.lastrowid)
            conn.execute(
                """
                UPDATE study_attempt_sessions
                SET solved_count = solved_count + 1,
                    correct_count = correct_count + CASE WHEN ? = 'correct' THEN 1 ELSE 0 END
                WHERE id = ?
                """,
                (final_status, session_id),
            )
            conn.commit()
        if final_status != "correct":
            self.upsert_wrong_answer(problem_id, session_id, record_id, user_answer)
        else:
            self.resolve_wrong_answer(problem_id)
        return record_id

    def finish_attempt_session(self, session_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE study_attempt_sessions
                SET status = 'completed', completed_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )
            conn.commit()

    def upsert_wrong_answer(
        self,
        problem_id: int,
        session_id: int,
        record_id: int,
        user_answer: str,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, wrong_count FROM study_wrong_answers WHERE problem_id = ?",
                (problem_id,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE study_wrong_answers
                    SET wrong_count = wrong_count + 1,
                        last_session_id = ?,
                        last_record_id = ?,
                        last_user_answer = ?,
                        is_resolved = 0,
                        last_wrong_at = ?,
                        updated_at = ?
                    WHERE problem_id = ?
                    """,
                    (session_id, record_id, user_answer, now, now, problem_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO study_wrong_answers (
                        problem_id, wrong_count, last_session_id, last_record_id,
                        last_user_answer, is_resolved, first_wrong_at,
                        last_wrong_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (problem_id, 1, session_id, record_id, user_answer, now, now, now),
                )
            conn.commit()

    def resolve_wrong_answer(self, problem_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE study_wrong_answers
                SET is_resolved = 1, updated_at = ?
                WHERE problem_id = ?
                """,
                (now, problem_id),
            )
            conn.commit()

    def list_wrong_answers(self, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        where_clause = "WHERE w.is_resolved = 0" if unresolved_only else ""
        query = f"""
            SELECT w.*, p.question_text, p.answer_text, p.problem_type
            FROM study_wrong_answers w
            JOIN study_problems p ON p.id = w.problem_id
            {where_clause}
            ORDER BY w.updated_at DESC
        """
        with self.get_connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def get_session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM study_attempt_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_attempt_records(self, session_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT r.*, p.question_text, p.answer_text, p.problem_type
                FROM study_attempt_records r
                JOIN study_problems p ON p.id = r.problem_id
                WHERE r.session_id = ?
                ORDER BY r.id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]
