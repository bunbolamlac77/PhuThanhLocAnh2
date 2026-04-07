import sqlite3
import os
from typing import List, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "culling_results.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Table for image processing metadata and scores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    filename TEXT,
                    file_size INTEGER,
                    status TEXT DEFAULT 'pending', -- pending, processing, completed, error
                    sharpness_score REAL,
                    blink_score REAL,
                    gaze_score REAL,
                    final_score REAL,
                    is_selected BOOLEAN DEFAULT 0,
                    group_id TEXT,
                    metadata TEXT, -- JSON string for extra data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_image(self, file_path: str, filename: str, file_size: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO images (file_path, filename, file_size) VALUES (?, ?, ?)",
                (file_path, filename, file_size)
            )
            conn.commit()

    def update_scores(self, file_path: str, sharpness: float, blink: float, gaze: float, final: float, is_selected: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE images 
                SET sharpness_score = ?, blink_score = ?, gaze_score = ?, final_score = ?, is_selected = ?, status = 'completed'
                WHERE file_path = ?
            """, (sharpness, blink, gaze, final, int(is_selected), file_path))
            conn.commit()

    def get_all_images(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM images ORDER BY final_score DESC")
            return [dict(row) for row in cursor.fetchall()]

# Global instance
db = DatabaseManager()
