import sqlite3
import os

from app import get_db

# Ensure database folder exists
if not os.path.exists("database"):
    os.makedirs("database")

# Connect to database (creates file if not exists)
conn = sqlite3.connect(os.path.join("database", "health.db"))
cursor = conn.cursor()

# =========================
# USERS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    height REAL,
    weight REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# HEALTH RECORDS TABLE
# (Expanded for 10 Diseases)
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS health_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,

    -- Basic Vitals
    heart_rate INTEGER,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    blood_sugar REAL,
    temperature REAL,
    oxygen_level REAL,
    bmi REAL,

    -- Extended Lab Inputs
    cholesterol REAL,
    hemoglobin REAL,
    creatinine REAL,
    tsh_level REAL,

    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

# =========================
# PREDICTIONS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    disease_name TEXT,
    probability REAL,
    risk_level TEXT,
    prediction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

# =========================
# CHATBOT HISTORY TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS chatbot_history (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_message TEXT,
    bot_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")
def init_fityoga_tables():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS yoga_programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        duration_days INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS enrolled_programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        program_id INTEGER,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        program_id INTEGER,
        day_completed INTEGER,
        completed INTEGER DEFAULT 1,
        UNIQUE(user_id, program_id, day_completed)
    )
    """)

    conn.commit()
    conn.close()
conn.commit()
conn.close()

print("Database and all tables created successfully.")
