"""
Database connection and lifecycle manager for SQLite.
Provides safe thread-local connections and row mapping for repositories.
"""
import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database",
    "auction.db"
)

def get_db_path() -> str:
    return os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Returns an SQLite connection configured with row factory and WAL mode.
    """
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path: Optional[str] = None, schema_file: Optional[str] = None) -> None:
    """
    Initializes the database schema if tables do not exist.
    """
    path = db_path or get_db_path()
    if schema_file is None:
        schema_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "schema.sql"
        )
    
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
