import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database", "health.db")

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE users
ADD COLUMN is_verified INTEGER DEFAULT 0;
""")

conn.commit()
conn.close()

print("Column added successfully.")
