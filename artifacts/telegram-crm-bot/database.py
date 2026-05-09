import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "crm.db")

DEFAULT_TAGS = [
    "⭐ VIP",
    "🆕 Новый",
    "✅ Постоянный",
    "⚠️ Проблемный",
    "💰 Должник",
]


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._create_tables()
        self._migrate()
        self._seed_tags()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                added_by_user_id INTEGER DEFAULT NULL,
                added_by_username TEXT DEFAULT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL UNIQUE,
                reason TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS client_tags (
                client_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (client_id, tag_id),
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def _migrate(self):
        for col, definition in [
            ("added_by_user_id", "INTEGER DEFAULT NULL"),
            ("added_by_username", "TEXT DEFAULT NULL"),
        ]:
            try:
                self.conn.execute(f"ALTER TABLE clients ADD COLUMN {col} {definition}")
                self.conn.commit()
            except sqlite3.OperationalError:
                pass

    def _seed_tags(self):
        existing = self.conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        if existing == 0:
            for name in DEFAULT_TAGS:
                self.conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
            self.conn.commit()

    def add_client(
        self,
        name: str,
        phone: str,
        email: str = "",
        notes: str = "",
        added_by_user_id: int = None,
        added_by_username: str = None,
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO clients
               (name, phone, email, notes, created_at, added_by_user_id, added_by_username)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, phone, email, notes, datetime.now().isoformat(),
             added_by_user_id, added_by_username)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_client(self, client_id: int):
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at,
                      added_by_user_id, added_by_username
               FROM clients WHERE id = ?""",
            (client_id,)
        )
        return cursor.fetchone()

    def get_all_clients(self):
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at,
                      added_by_user_id, added_by_username
               FROM clients ORDER BY name ASC"""
        )
        return cursor.fetchall()

    def search_by_name(self, query: str):
        like = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at,
                      added_by_user_id, added_by_username
               FROM clients WHERE name LIKE ? ORDER BY name ASC""",
            (like,)
        )
        return cursor.fetchall()

    def search_by_phone(self, query: str):
        like = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at,
                      added_by_user_id, added_by_username
               FROM clients WHERE phone LIKE ? ORDER BY name ASC""",
            (like,)
        )
        return cursor.fetchall()

    def update_client_field(self, client_id: int, field: str, value: str):
        allowed = {"name", "phone", "email", "notes"}
        if field not in allowed:
            raise ValueError(f"Invalid field: {field}")
        self.conn.execute(
            f"UPDATE clients SET {field} = ? WHERE id = ?",
            (value, client_id)
        )
        self.conn.commit()

    def delete_client(self, client_id: int):
        self.conn.execute("DELETE FROM client_tags WHERE client_id = ?", (client_id,))
        self.conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self.conn.commit()

    def add_to_blacklist(self, phone: str, reason: str = "") -> bool:
        try:
            self.conn.execute(
                "INSERT INTO blacklist (phone, reason, created_at) VALUES (?, ?, ?)",
                (phone, reason, datetime.now().isoformat())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_blacklist(self):
        cursor = self.conn.execute(
            "SELECT id, phone, reason, created_at FROM blacklist ORDER BY created_at DESC"
        )
        return cursor.fetchall()

    def remove_from_blacklist(self, phone: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM blacklist WHERE phone = ?", (phone,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def is_blacklisted(self, phone: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM blacklist WHERE phone = ?", (phone,)
        )
        return cursor.fetchone() is not None

    def get_all_tags(self):
        cursor = self.conn.execute("SELECT id, name FROM tags ORDER BY id")
        return cursor.fetchall()

    def get_client_tags(self, client_id: int):
        cursor = self.conn.execute(
            """SELECT t.id, t.name FROM tags t
               JOIN client_tags ct ON ct.tag_id = t.id
               WHERE ct.client_id = ?
               ORDER BY t.id""",
            (client_id,)
        )
        return cursor.fetchall()

    def set_client_tags(self, client_id: int, tag_ids: list):
        self.conn.execute("DELETE FROM client_tags WHERE client_id = ?", (client_id,))
        for tag_id in tag_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO client_tags (client_id, tag_id) VALUES (?, ?)",
                (client_id, tag_id)
            )
        self.conn.commit()

    def get_clients_by_tag(self, tag_id: int):
        cursor = self.conn.execute(
            """SELECT c.id, c.name, c.phone, c.email, c.notes, c.created_at,
                      c.added_by_user_id, c.added_by_username
               FROM clients c
               JOIN client_tags ct ON ct.client_id = c.id
               WHERE ct.tag_id = ?
               ORDER BY c.name ASC""",
            (tag_id,)
        )
        return cursor.fetchall()
