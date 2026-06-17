import sqlite3
import json
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shield_history.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,          -- 'image', 'video', 'audio', 'text'
            input_source NOT NULL,       -- file name or URL
            verdict TEXT NOT NULL,
            confidence REAL NOT NULL,
            risk TEXT NOT NULL,
            signals TEXT,
            explanation TEXT,
            details TEXT,                -- JSON string for extra info (like frame details, transcription)
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_history_item(item_type, input_source, verdict, confidence, risk, signals, explanation, details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Safely convert details dict/list to JSON string
    details_str = json.dumps(details) if details is not None else None
    
    # Strip percent signs from confidence if passed as string, e.g. "95%"
    try:
        if isinstance(confidence, str):
            confidence = float(confidence.replace('%', '').strip())
        else:
            confidence = float(confidence)
    except Exception:
        confidence = 0.0

    cursor.execute("""
        INSERT INTO history (type, input_source, verdict, confidence, risk, signals, explanation, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_type, input_source, verdict, confidence, risk, signals, explanation, details_str))
    
    conn.commit()
    conn.close()

def get_history(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        item = dict(row)
        if item["details"]:
            try:
                item["details"] = json.loads(item["details"])
            except Exception:
                pass
        results.append(item)
        
    conn.close()
    return results

def clear_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()
