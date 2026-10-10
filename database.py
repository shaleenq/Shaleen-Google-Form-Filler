import sqlite3
import json
import os
import random
import string
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiting_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                access_key TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_key TEXT UNIQUE NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
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


# ==========================================
# ACCESS CONTROL FUNCTIONS
# ==========================================

def verify_access_key(access_key: str, db_path=DB_FILE) -> bool:
    """Verifies if an access key is valid and active."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM access_keys WHERE access_key = ? AND is_active = 1", (access_key.strip(),))
        return cursor.fetchone() is not None

def add_to_waiting_list(name: str, contact: str, db_path=DB_FILE) -> int:
    """Adds a user to the waiting list. Returns the new row ID."""
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO waiting_list (name, contact, status, created_at)
            VALUES (?, ?, 'PENDING', ?)
        """, (name.strip(), contact.strip(), now_str))
        conn.commit()
        return cursor.lastrowid

def get_waiting_list(db_path=DB_FILE):
    """Retrieves all waiting list entries."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM waiting_list ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def approve_user(waiting_id: int, access_key: str = None, db_path=DB_FILE) -> bool:
    """Approves a waiting list user and generates an access key."""
    init_db(db_path)
    if access_key is None:
        access_key = f"SHALEEN_{random.randint(10000, 99999)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Update waiting list
        cursor.execute("""
            UPDATE waiting_list SET status = 'APPROVED', access_key = ? WHERE id = ?
        """, (access_key, waiting_id))
        # Add to access_keys table
        cursor.execute("""
            INSERT INTO access_keys (access_key, is_active, created_at)
            VALUES (?, 1, ?)
        """, (access_key, now_str))
        conn.commit()
        return cursor.rowcount > 0

def generate_access_key(db_path=DB_FILE) -> str:
    """Generates a new unique access key."""
    init_db(db_path)
    while True:
        key = f"SHALEEN_{random.randint(10000, 99999)}"
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM access_keys WHERE access_key = ?", (key,))
            if not cursor.fetchone():
                return key
