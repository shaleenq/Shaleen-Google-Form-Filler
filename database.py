import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "form_presets.db"

def get_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_FILE):
    """Initializes the SQLite database table for form presets."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS form_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_name TEXT UNIQUE NOT NULL,
                form_url TEXT NOT NULL,
                page_history TEXT NOT NULL,
                questions_config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

def save_preset(preset_name: str, form_url: str, page_history: str, questions_config: dict, db_path=DB_FILE) -> bool:
    """Saves or updates a preset configuration."""
    init_db(db_path)
    questions_config_json = json.dumps(questions_config, ensure_ascii=False)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO form_presets (preset_name, form_url, page_history, questions_config_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(preset_name) DO UPDATE SET
                form_url=excluded.form_url,
                page_history=excluded.page_history,
                questions_config_json=excluded.questions_config_json,
                updated_at=excluded.updated_at
        """, (preset_name.strip(), form_url.strip(), page_history, questions_config_json, now_str))
        conn.commit()
    return True

def get_all_presets(db_path=DB_FILE):
    """Retrieves list of all saved presets with summary information."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, preset_name, form_url, page_history, updated_at FROM form_presets ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_preset(preset_name: str, db_path=DB_FILE):
    """Retrieves a single preset by name."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM form_presets WHERE preset_name = ?", (preset_name,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["questions_config"] = json.loads(d["questions_config_json"])
            return d
        return None

def delete_preset(preset_name: str, db_path=DB_FILE) -> bool:
    """Deletes a preset by name."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM form_presets WHERE preset_name = ?", (preset_name,))
        conn.commit()
        return cursor.rowcount > 0
