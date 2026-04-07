import sqlite3
import os

DB_FILE = "culling_state.db"

def init_db():
    """Khởi tạo bảng cơ sở dữ liệu SQLite"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Bảng lưu thông tin ảnh đã phân tích
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            scene_cluster INTEGER DEFAULT -1,
            pose_cluster INTEGER DEFAULT -1,
            sharpness_score REAL DEFAULT 0.0,
            face_score REAL DEFAULT 0.0,
            total_score REAL DEFAULT 0.0,
            is_selected BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def save_image_record(file_path, total_score):
    """Lưu kết quả phân tích của 1 ảnh"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO images (file_path, total_score)
        VALUES (?, ?)
    ''', (file_path, total_score))
    conn.commit()
    conn.close()
    
def save_image_record(file_path, total_score):
    """Lưu kết quả phân tích của 1 ảnh"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO images (file_path, total_score)
        VALUES (?, ?)
    ''', (file_path, total_score))
    conn.commit()
    conn.close()
