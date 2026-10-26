"""
User repository for Member 1 user lookup and authentication queries.
Uses parameterized SQLite queries.
"""
from typing import Optional, Dict, Any
from database.db import get_connection

class UserRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a user by exact username.
        Returns a dict with user fields or None if not found.
        """
        if not username or not username.strip():
            return None
        
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, username, display_name, role, created_at
                FROM users
                WHERE LOWER(username) = LOWER(?)
                LIMIT 1;
                """,
                (username.strip(),)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a user by unique user_id.
        """
        if not user_id:
            return None

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, username, display_name, role, created_at
                FROM users
                WHERE user_id = ?
                LIMIT 1;
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
