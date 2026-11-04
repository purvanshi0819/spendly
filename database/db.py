import sqlite3
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash


DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"


def get_db():
    """Return a sqlite3 connection with Row factory and FK enforcement enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not already exist."""
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert demo data once; skip if users already exist."""
    conn = get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        first_day = date(date.today().year, date.today().month, 1)
        sample_expenses = [
            ("Food", 350.00, "Lunch at cafe"),
            ("Transport", 120.00, "Metro fare"),
            ("Bills", 1200.00, "Electricity bill"),
            ("Health", 500.00, "Pharmacy visit"),
            ("Entertainment", 800.00, "Movie night"),
            ("Shopping", 2500.00, "Grocery run"),
            ("Other", 300.00, "Miscellaneous"),
            ("Food", 450.00, "Dinner with friends"),
        ]

        for offset, (category, amount, description) in enumerate(sample_expenses):
            expense_date = first_day + timedelta(days=offset)
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, amount, category, expense_date.isoformat(), description),
            )

        conn.commit()
    finally:
        conn.close()

def create_user(name, email, password_hash):
    """Insert a new user and return the new row id."""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row matching email, or None if no such user exists."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row matching id, or None if no such user exists."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def get_expenses_by_user(user_id):
    """Return the user's expenses ordered by date desc, then id desc."""
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT * FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

