"""
Database management for Local Skill & Job Exchange Platform.
Community Engineering Project (BIT42304) - TGPCET Nagpur
"""

import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "platform.db")


def get_db_connection():
    """Create and return a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session():
    """Context manager for safe database transaction handling."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(force=False):
    """Initialize database tables according to the project specifications."""
    if force and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    with db_session() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'both', -- 'provider', 'requester', 'both', 'admin'
            phone TEXT,
            neighborhood TEXT NOT NULL DEFAULT 'Nagpur Central',
            city TEXT NOT NULL DEFAULT 'Nagpur',
            lat REAL DEFAULT 21.1458,
            lng REAL DEFAULT 79.0882,
            bio TEXT,
            avatar TEXT,
            rating REAL DEFAULT 5.0,
            total_reviews INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active', -- 'active', 'suspended', 'pending'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Skills Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            hourly_rate REAL NOT NULL DEFAULT 0.0,
            experience_years INTEGER NOT NULL DEFAULT 1,
            neighborhood TEXT NOT NULL,
            lat REAL DEFAULT 21.1458,
            lng REAL DEFAULT 79.0882,
            availability TEXT NOT NULL DEFAULT 'flexible', -- 'full-time', 'part-time', 'weekends', 'flexible'
            tags TEXT, -- comma-separated tags
            status TEXT DEFAULT 'active', -- 'active', 'inactive'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 3. Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            budget REAL NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'emergency'
            neighborhood TEXT NOT NULL,
            lat REAL DEFAULT 21.1458,
            lng REAL DEFAULT 79.0882,
            max_distance_km REAL DEFAULT 15.0,
            assigned_provider_id INTEGER,
            status TEXT DEFAULT 'open', -- 'open', 'in_progress', 'completed', 'cancelled'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_provider_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)

        # 4. Direct Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            job_id INTEGER,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );
        """)

        # 5. Reviews & Feedback Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            reviewer_id INTEGER NOT NULL,
            reviewee_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
            FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reviewee_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 6. Activity Logs Table (for Admin Monitoring)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT DEFAULT '127.0.0.1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)

        # 7. Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # Indexes for fast search
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_neighborhood ON skills(neighborhood);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(sender_id, receiver_id);")

        print("Database initialized successfully.")
