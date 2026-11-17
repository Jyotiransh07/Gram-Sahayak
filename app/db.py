"""Simple local database; all public endpoints remain localhost-only by default."""
import sqlite3
import json
from datetime import datetime, timezone
from .config import DB_FILE


def connect():
    db = sqlite3.connect(DB_FILE, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            language TEXT NOT NULL,
            created_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profiles(
            session_id TEXT PRIMARY KEY,
            city TEXT,
            district TEXT,
            crop TEXT,
            language TEXT NOT NULL DEFAULT 'en',
            consent INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cache(
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reminders(
            id TEXT PRIMARY KEY, chat_id TEXT NOT NULL,
            message TEXT NOT NULL, due_utc TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
            body, source UNINDEXED, page UNINDEXED, source_url UNINDEXED
        );
        ''')


def store_message(session_id, role, content, language='en'):
    if not session_id or not content:
        return
    with connect() as db:
        db.execute('INSERT INTO messages(session_id, role, content, language, created_utc) VALUES (?, ?, ?, ?, ?)',
                   (session_id, role, str(content)[:20000], language, datetime.now(timezone.utc).isoformat()))


def get_history(session_id, limit=12):
    with connect() as db:
        rows = db.execute('SELECT role, content, language, created_utc FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?',
                          (session_id, min(max(1, int(limit)), 40))).fetchall()
    return [dict(row) for row in reversed(rows)]


def save_profile(session_id, city='', district='', crop='', language='en', consent=False):
    if not consent:
        return False
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO profiles(session_id, city, district, crop, language, consent) VALUES (?, ?, ?, ?, ?, 1)',
                   (session_id, city[:120], district[:120], crop[:100], language if language in ('hi', 'en') else 'en'))
    return True


def get_profile(session_id):
    with connect() as db:
        row = db.execute('SELECT city, district, crop, language, consent FROM profiles WHERE session_id=?', (session_id,)).fetchone()
    return dict(row) if row else None


def delete_user_data(session_id):
    with connect() as db:
        db.execute('DELETE FROM messages WHERE session_id=?', (session_id,))
        db.execute('DELETE FROM profiles WHERE session_id=?', (session_id,))


def get_cache(key, ttl_seconds):
    from datetime import timedelta
    with connect() as db:
        row = db.execute('SELECT value, updated_utc FROM cache WHERE key=?', (key,)).fetchone()
    if row:
        saved = datetime.fromisoformat(row['updated_utc'])
        if datetime.now(timezone.utc) - saved < timedelta(seconds=ttl_seconds):
            return json.loads(row['value'])
    return None


def put_cache(key, value):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO cache(key, value, updated_utc) VALUES (?, ?, ?)',
                   (key, json.dumps(value, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))


initialize()
