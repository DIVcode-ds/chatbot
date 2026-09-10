import os
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(os.getenv("DATABASE_PATH", "nova.db"))

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat',
            persona TEXT NOT NULL DEFAULT 'general',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        db.execute("""
        INSERT OR IGNORE INTO conversations (id, user_id, title, created_at, updated_at)
        SELECT conversation_id, user_id, 'New chat', MIN(created_at), MAX(created_at)
        FROM messages GROUP BY conversation_id, user_id
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(user_id, conversation_id, id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC)")
        db.commit()

def create_user(name, email, password_hash):
    with conn() as db:
        cur = db.execute(
            "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
            (name, email, password_hash),
        )
        db.commit()
        return cur.lastrowid

def get_user(email):
    with conn() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

def create_conversation(user_id, persona="general", conversation_id=None):
    conversation_id = conversation_id or str(uuid.uuid4())
    with conn() as db:
        db.execute("INSERT INTO conversations(id,user_id,persona) VALUES(?,?,?)", (conversation_id, user_id, persona))
        db.commit()
    return get_conversation(user_id, conversation_id)

def get_conversation(user_id, conversation_id):
    with conn() as db:
        row = db.execute("SELECT * FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone()
        return dict(row) if row else None

def get_conversations(user_id):
    with conn() as db:
        rows = db.execute("""SELECT c.id, c.title, c.persona, c.created_at, c.updated_at, COUNT(m.id) AS message_count
               FROM conversations c LEFT JOIN messages m ON m.user_id=c.user_id AND m.conversation_id=c.id
               WHERE c.user_id=? GROUP BY c.id ORDER BY c.updated_at DESC""", (user_id,)).fetchall()
        return [dict(row) for row in rows]

def update_conversation(user_id, conversation_id, title=None, persona=None):
    changes, values = [], []
    if title is not None:
        changes.append("title=?"); values.append(title)
    if persona is not None:
        changes.append("persona=?"); values.append(persona)
    if not changes:
        return get_conversation(user_id, conversation_id)
    changes.append("updated_at=CURRENT_TIMESTAMP")
    values.extend([conversation_id, user_id])
    with conn() as db:
        db.execute(f"UPDATE conversations SET {', '.join(changes)} WHERE id=? AND user_id=?", values)
        db.commit()
    return get_conversation(user_id, conversation_id)

def delete_conversation(user_id, conversation_id):
    with conn() as db:
        db.execute("DELETE FROM messages WHERE user_id=? AND conversation_id=?", (user_id, conversation_id))
        cur = db.execute("DELETE FROM conversations WHERE user_id=? AND id=?", (user_id, conversation_id))
        db.commit()
        return cur.rowcount > 0

def save_message(user_id, conversation_id, role, content):
    with conn() as db:
        db.execute(
            "INSERT INTO messages(user_id,conversation_id,role,content) VALUES(?,?,?,?)",
            (user_id, conversation_id, role, content),
        )
        db.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?", (conversation_id, user_id))
        db.commit()

def get_messages(user_id, conversation_id):
    with conn() as db:
        rows = db.execute(
            """SELECT role, content, created_at
               FROM messages
               WHERE user_id=? AND conversation_id=?
               ORDER BY id ASC""",
            (user_id, conversation_id),
        ).fetchall()
        return [dict(r) for r in rows]
