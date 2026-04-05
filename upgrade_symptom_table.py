import sqlite3

conn = sqlite3.connect("database/health.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS symptom_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    age INTEGER,
    sex TEXT,
    symptoms TEXT,
    predicted_disease TEXT,
    probability REAL,
    risk_level TEXT,
    confidence REAL,
    hospital_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Symptom assessment table upgraded successfully.")
