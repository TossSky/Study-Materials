from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

DB_PATH = os.environ.get("DB_PATH", "users.db")
_LOCK = threading.Lock()
_PBKDF2_ITER = 200_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id      INTEGER PRIMARY KEY,
    password_hash BLOB    NOT NULL,
    password_salt BLOB    NOT NULL,
    logged_in    INTEGER NOT NULL DEFAULT 0,
    pending      TEXT    NOT NULL DEFAULT ''
);
"""


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITER)


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    with _LOCK:
        c = sqlite3.connect(DB_PATH)
        try:
            c.execute("PRAGMA journal_mode=WAL;")
            yield c
            c.commit()
        finally:
            c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def register(chat_id: int, password: str) -> bool:
    salt = secrets.token_bytes(16)
    pwd_hash = _hash_password(password, salt)
    with _conn() as c:
        cur = c.execute("SELECT 1 FROM users WHERE chat_id=?", (chat_id,))
        if cur.fetchone() is not None:
            return False
        c.execute(
            "INSERT INTO users(chat_id, password_hash, password_salt) VALUES (?,?,?)",
            (chat_id, pwd_hash, salt),
        )
        return True


def verify(chat_id: int, password: str) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT password_hash, password_salt FROM users WHERE chat_id=?",
            (chat_id,),
        ).fetchone()
    if row is None:
        return False
    stored_hash, salt = row
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


def set_logged_in(chat_id: int, value: bool) -> None:
    with _conn() as c:
        c.execute("UPDATE users SET logged_in=? WHERE chat_id=?", (1 if value else 0, chat_id))


def is_logged_in(chat_id: int) -> bool:
    with _conn() as c:
        row = c.execute("SELECT logged_in FROM users WHERE chat_id=?", (chat_id,)).fetchone()
    return bool(row and row[0])


def set_pending(chat_id: int, pending: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO users(chat_id, password_hash, password_salt, pending)"
            " VALUES (?, x'', x'', ?)"
            " ON CONFLICT(chat_id) DO UPDATE SET pending=excluded.pending",
            (chat_id, pending),
        )


def get_pending(chat_id: int) -> Optional[str]:
    with _conn() as c:
        row = c.execute("SELECT pending FROM users WHERE chat_id=?", (chat_id,)).fetchone()
    return row[0] if row and row[0] else None


def clear_pending(chat_id: int) -> None:
    set_pending(chat_id, "")


def exists(chat_id: int) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM users WHERE chat_id=? AND length(password_hash)>0",
            (chat_id,),
        ).fetchone()
    return row is not None
