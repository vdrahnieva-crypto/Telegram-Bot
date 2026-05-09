import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "crm.db")


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
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
        self.conn.commit()

    def add_client(self, name: str, phone: str, email: str = "", notes: str = "") -> int:
        cursor = self.conn.execute(
            "INSERT INTO clients (name, phone, email, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, phone, email, notes, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_client(self, client_id: int):
        cursor = self.conn.execute(
            "SELECT id, name, phone, email, notes, created_at FROM clients WHERE id = ?",
            (client_id,)
        )
        return cursor.fetchone()

    def get_all_clients(self):
        cursor = self.conn.execute(
            "SELECT id, name, phone, email, notes, created_at FROM clients ORDER BY name ASC"
        )
        return cursor.fetchall()

    def search_clients(self, query: str):
        like = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at FROM clients
               WHERE name LIKE ? OR phone LIKE ?
               ORDER BY name ASC""",
            (like, like)
        )
        return cursor.fetchall()

    def search_by_name(self, query: str):
        like = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at FROM clients
               WHERE name LIKE ?
               ORDER BY name ASC""",
            (like,)
        )
        return cursor.fetchall()

    def search_by_phone(self, query: str):
        like = f"%{query}%"
        cursor = self.conn.execute(
            """SELECT id, name, phone, email, notes, created_at FROM clients
               WHERE phone LIKE ?
               ORDER BY name ASC""",
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
