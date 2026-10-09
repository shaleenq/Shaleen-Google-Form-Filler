import sqlite3
import json
import os
from datetime import datetime
import pandas as pd

DB_FILE = "form_presets.db"

def get_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_FILE):
    """Initializes the SQLite database tables for form presets, access keys, and waiting list."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Form presets table
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
        
        # Access keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Waiting list table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiting_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                access_key TEXT,
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

def verify_access_key(access_key: str, db_path=DB_FILE) -> bool:
    """Verifies if an access key is valid and active."""
    if not access_key or not access_key.strip():
        return False
    
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM access_keys WHERE access_key = ? AND is_active = 1",
            (access_key.strip(),)
        )
        result = cursor.fetchone()
        return result['count'] > 0 if result else False

def add_to_waiting_list(name: str, contact: str, db_path=DB_FILE) -> bool:
    """Adds a user to the waiting list."""
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO waiting_list (name, contact, status, created_at) VALUES (?, ?, ?, ?)",
                (name.strip(), contact.strip(), 'PENDING', now_str)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding to waiting list: {e}")
            return False

def get_waiting_list(db_path=DB_FILE):
    """Retrieves the waiting list as a pandas DataFrame."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, contact, status, access_key, created_at FROM waiting_list ORDER BY created_at ASC"
        )
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
    
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=['id', 'name', 'contact', 'status', 'access_key', 'created_at'])
    return df

def approve_user(waiting_list_id: int, access_key: str, db_path=DB_FILE) -> bool:
    """Approves a waiting list user and generates an access key."""
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        try:
            # Insert the new access key
            cursor.execute(
                "INSERT INTO access_keys (access_key, created_at, is_active) VALUES (?, ?, ?)",
                (access_key, now_str, 1)
            )
            
            # Update the waiting list entry
            cursor.execute(
                "UPDATE waiting_list SET status = ?, access_key = ? WHERE id = ?",
                ('APPROVED', access_key, waiting_list_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error approving user: {e}")
            return False
