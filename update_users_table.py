import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database", "health.db")

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS symptom_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    age INTEGER,
    sex TEXT,
    symptoms TEXT,
    predicted_disease TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()

print("Column added successfully.")
