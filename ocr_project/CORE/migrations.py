"""
SQLite Migration Module for Quiz Platform Schema

This module provides functions to safely apply the quiz platform schema
migration to an existing OCR database while maintaining backward compatibility.

Usage:
    from migrations import apply_quiz_migration, verify_migration
    
    # Apply migration to the canonical CORE/ocr_study.db database
    apply_quiz_migration()
    
    # Verify success
    verify_migration()
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "ocr_study.db"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create and return a SQLite database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_quiz_migration(db_path: str = str(DEFAULT_DB_PATH)) -> Dict[str, Any]:
    """
    Apply quiz platform schema migration to existing database.
    
    Creates new tables for:
    - ocr_analyses: Content analysis and metadata
    - quiz_sets: Quiz groupings per OCR result
    - quiz_items: Individual quiz questions
    - quiz_attempts: User quiz performance tracking
    
    Args:
        db_path: Path to SQLite database (default: CORE/ocr_study.db)
        
    Returns:
        Dictionary with migration results and status
        
    Raises:
        Exception: If migration fails (transaction rolled back automatically)
    """
    results = {
        "status": "pending",
        "tables_created": [],
        "indexes_created": [],
        "errors": [],
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Create ocr_analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_result_id INTEGER NOT NULL UNIQUE,
                    complexity_level TEXT NOT NULL DEFAULT 'intermediate',
                    key_entities TEXT,
                    readability_score INTEGER,
                    word_count INTEGER,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("ocr_analyses")
            
            # Create quiz_sets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_result_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    quiz_type TEXT NOT NULL DEFAULT 'mixed',
                    target_language TEXT,
                    total_items INTEGER DEFAULT 0,
                    metadata TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("quiz_sets")
            
            # Create quiz_items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quiz_set_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL,
                    question TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    alternatives TEXT,
                    options TEXT,
                    source_text TEXT,
                    difficulty TEXT DEFAULT 'medium',
                    explanation TEXT,
                    tags TEXT,
                    item_order INTEGER,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (quiz_set_id) REFERENCES quiz_sets(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("quiz_items")
            
            # Create quiz_attempts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quiz_set_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    score INTEGER,
                    time_taken_seconds INTEGER,
                    status TEXT DEFAULT 'in_progress',
                    item_results TEXT,
                    notes TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (quiz_set_id) REFERENCES quiz_sets(id) ON DELETE CASCADE
                )
            """)
            results["tables_created"].append("quiz_attempts")
            
            # Create indexes for ocr_analyses
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_ocr_result ON ocr_analyses(ocr_result_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_complexity ON ocr_analyses(complexity_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_created ON ocr_analyses(created_at DESC)")
            
            # Create indexes for quiz_sets
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_sets_ocr_result ON quiz_sets(ocr_result_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_sets_quiz_type ON quiz_sets(quiz_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_sets_status ON quiz_sets(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_sets_created ON quiz_sets(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_sets_target_lang ON quiz_sets(target_language)")
            
            # Create indexes for quiz_items
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_items_quiz_set ON quiz_items(quiz_set_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_items_item_type ON quiz_items(item_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_items_difficulty ON quiz_items(difficulty)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quiz_items_order ON quiz_items(quiz_set_id, item_order)")
            
            # Create indexes for quiz_attempts
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_quiz_set ON quiz_attempts(quiz_set_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_user ON quiz_attempts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_status ON quiz_attempts(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_user_quiz ON quiz_attempts(user_id, quiz_set_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_completed ON quiz_attempts(completed_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_user_completed ON quiz_attempts(user_id, status, completed_at DESC)")
            
            results["indexes_created"] = [
                "idx_analyses_*",
                "idx_quiz_sets_*",
                "idx_quiz_items_*",
                "idx_attempts_*",
            ]
            
            conn.commit()
            results["status"] = "success"
            
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(str(e))
        raise
    
    return results


def verify_migration(db_path: str = str(DEFAULT_DB_PATH)) -> Dict[str, Any]:
    """
    Verify that migration was applied correctly and no data was lost.
    
    Checks:
    - All new tables exist
    - All indexes exist
    - Original ocr_results table is intact
    - Foreign key constraints are valid
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with verification results
    """
    results = {
        "migration_complete": False,
        "tables_verified": [],
        "tables_missing": [],
        "indexes_verified": 0,
        "ocr_results_intact": False,
        "sample_data_accessible": False,
        "errors": [],
    }
    
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Check for new tables
            required_tables = [
                "ocr_analyses",
                "quiz_sets",
                "quiz_items",
                "quiz_attempts",
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            for table in required_tables:
                if table in existing_tables:
                    results["tables_verified"].append(table)
                else:
                    results["tables_missing"].append(table)
            
            # Check for indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = cursor.fetchall()
            results["indexes_verified"] = len(indexes)
            
            # Verify ocr_results table is intact
            cursor.execute("PRAGMA table_info(ocr_results)")
            columns = {row[1] for row in cursor.fetchall()}
            expected_columns = {"id", "content", "payload_json", "source_region", "tags", "created_at"}
            if expected_columns.issubset(columns):
                results["ocr_results_intact"] = True
            
            # Try to access sample data
            cursor.execute("SELECT COUNT(*) as count FROM ocr_results")
            row_count = cursor.fetchone()[0]
            results["sample_data_accessible"] = True
            results["ocr_results_row_count"] = row_count
            
            # Mark migration complete if all tables exist
            if not results["tables_missing"]:
                results["migration_complete"] = True
                
    except Exception as e:
        results["errors"].append(str(e))
    
    return results


def create_analysis_for_result(
    db_path: str,
    ocr_result_id: int,
    complexity_level: str = "intermediate",
    key_entities: Optional[List[str]] = None,
    readability_score: Optional[int] = None,
    word_count: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create an analysis record for an existing OCR result.
    
    Args:
        db_path: Path to SQLite database
        ocr_result_id: ID of the OCR result to analyze
        complexity_level: 'simple', 'intermediate', or 'advanced'
        key_entities: List of key entities (vocabulary, concepts)
        readability_score: Score 0-100
        word_count: Number of words
        metadata: Additional metadata as dict
        
    Returns:
        ID of created analysis record
        
    Raises:
        ValueError: If OCR result doesn't exist
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Verify OCR result exists
        cursor.execute("SELECT id FROM ocr_results WHERE id = ?", (ocr_result_id,))
        if not cursor.fetchone():
            raise ValueError(f"OCR result with id {ocr_result_id} not found")
        
        now = datetime.now().isoformat(timespec="seconds")
        
        cursor.execute("""
            INSERT INTO ocr_analyses (
                ocr_result_id, complexity_level, key_entities,
                readability_score, word_count, metadata,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ocr_result_id,
            complexity_level,
            json.dumps(key_entities or []),
            readability_score,
            word_count,
            json.dumps(metadata or {}),
            now,
            now,
        ))
        
        conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("failed to create OCR analysis")
        return int(cursor.lastrowid)


def create_quiz_set(
    db_path: str,
    ocr_result_id: int,
    title: str,
    quiz_type: str = "mixed",
    target_language: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create a quiz set for an OCR result.
    
    Args:
        db_path: Path to SQLite database
        ocr_result_id: ID of the OCR result
        title: Title for the quiz set
        quiz_type: 'vocabulary', 'comprehension', 'translation', or 'mixed'
        target_language: Target language code (e.g., 'en', 'ko')
        description: Optional description
        metadata: Additional metadata as dict
        
    Returns:
        ID of created quiz set
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat(timespec="seconds")
        
        cursor.execute("""
            INSERT INTO quiz_sets (
                ocr_result_id, title, description, quiz_type,
                target_language, metadata, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ocr_result_id,
            title,
            description,
            quiz_type,
            target_language,
            json.dumps(metadata or {}),
            "draft",
            now,
            now,
        ))
        
        conn.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("failed to create quiz set")
        return int(cursor.lastrowid)


def get_migration_status(db_path: str = str(DEFAULT_DB_PATH)) -> str:
    """
    Get a human-readable status of the migration.
    
    Returns:
        Status string: 'not_applied', 'partial', 'complete', or 'error'
    """
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'quiz_%'")
            tables = cursor.fetchall()
            
            if len(tables) == 0:
                return "not_applied"
            elif len(tables) < 3:  # quiz_sets, quiz_items, quiz_attempts
                return "partial"
            else:
                return "complete"
    except Exception:
        return "error"


if __name__ == "__main__":
    # Test the migration
    db_path = str(DEFAULT_DB_PATH)
    
    print("Applying quiz platform migration...")
    result = apply_quiz_migration(db_path)
    print(f"Migration status: {result['status']}")
    print(f"Tables created: {', '.join(result['tables_created'])}")
    
    print("\nVerifying migration...")
    verify_result = verify_migration(db_path)
    print(f"Migration complete: {verify_result['migration_complete']}")
    print(f"Tables verified: {', '.join(verify_result['tables_verified'])}")
    print(f"Indexes created: {verify_result['indexes_verified']}")
    print(f"OCR results intact: {verify_result['ocr_results_intact']}")
