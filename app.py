from http import client

from translations_dict import TEXT

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)
from flask_babel import Babel, _
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from email.mime.text import MIMEText

import os
import smtplib
import random
import sqlite3
import joblib
import requests
import math
from datetime import datetime, timedelta



# ============================
# App Initialization
# ============================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "healthtrackk_secret_2026")


app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_SUPPORTED_LOCALES"] = ["en", "hi", "mr"]


# ============================
# OpenRouter / AI Client
# ============================



import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)


# ============================
# Translation Helper
# ============================

def t(key):
    lang = session.get("lang", "en")
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))


@app.context_processor
def inject_translator():
    return dict(t=t)


babel = Babel()


def get_locale():
    return session.get("lang", "en")


babel.init_app(app, locale_selector=get_locale)


# ============================
# Email Configuration
# ============================

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "healthtrackk.pvt.ltd@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "cbrfnstiirrimzwm")


# ============================
# Paths
# ============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database", "health.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(cursor, table_name, column_name, definition):
    columns = {
        row["name"]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_app_database():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_verified INTEGER DEFAULT 0
        )
        """
    )

    ensure_column(cursor, "users", "is_verified", "INTEGER DEFAULT 0")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS health_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            heart_rate INTEGER,
            systolic_bp INTEGER,
            diastolic_bp INTEGER,
            blood_sugar REAL,
            temperature REAL,
            oxygen_level REAL,
            bmi REAL,
            cholesterol REAL,
            hemoglobin REAL,
            creatinine REAL,
            tsh_level REAL,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    for column_name, definition in [
        ("notes", "TEXT"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]:
        ensure_column(cursor, "health_records", column_name, definition)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vaccinations (
            vaccination_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vaccine_name TEXT NOT NULL,
            dose_label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            due_date TEXT,
            administered_date TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            blood_group TEXT,
            allergies TEXT,
            chronic_conditions TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            primary_goal TEXT,
            city TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            disease_name TEXT,
            probability REAL,
            risk_level TEXT,
            prediction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chatbot_history (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS symptom_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            age INTEGER,
            sex TEXT,
            symptoms TEXT,
            predicted_disease TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    conn.commit()
    conn.close()
def init_fityoga_tables():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS yoga_programs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            description   TEXT    NOT NULL,
            duration_days INTEGER NOT NULL DEFAULT 7
        );

        CREATE TABLE IF NOT EXISTS enrolled_programs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            program_id  INTEGER NOT NULL,
            start_date  TEXT    DEFAULT (date('now')),
            UNIQUE(user_id, program_id)
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            program_id    INTEGER NOT NULL,
            day_completed INTEGER NOT NULL,
            completed     INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, program_id, day_completed)
        );
    """)
    conn.commit()

def seed_fityoga_data():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM yoga_programs").fetchone()[0] > 0:
        return

    programs = [
        (1, "7-Day Beginner Yoga",        "Start your yoga journey with gentle, guided daily sessions.",                     7),
        (2, "14-Day Flexibility Reset",    "Deep stretch and mobility training to unlock your body.",                        14),
        (3, "Heart Wellness Routine",      "Cardio-friendly yoga to support heart health daily.",                            30),
        (4, "Stress Relief Flow",          "Breathwork + restorative yoga for deep mental relief.",                         10),
        (5, "Desk Worker Stretch Plan",    "Targeted routines for office professionals and remote workers.",                 21),
        (6, "Deep Sleep Program",          "Evening routines and meditations for restful, deep sleep.",                      7),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO yoga_programs (id, name, description, duration_days) VALUES (?,?,?,?)",
        programs
    )
    conn.commit()    

def row_to_dict(row):
    return dict(row) if row is not None else {}


init_app_database()


# ============================
# Load ML Models
# ============================

def safe_load(path):
    try:
        return joblib.load(path)
    except Exception as e:
        print("MODEL LOAD ERROR:", e)
        return None

diabetes_model = safe_load(os.path.join(BASE_DIR, "models", "diabetes_model.pkl"))
heart_model = safe_load(os.path.join(BASE_DIR, "models", "heart_model.pkl"))
stroke_model = safe_load(os.path.join(BASE_DIR, "models", "stroke_model.pkl"))
chatbot_model = safe_load(os.path.join(BASE_DIR, "models", "chatbot_intent_model.pkl"))
vectorizer = safe_load(os.path.join(BASE_DIR, "models", "chatbot_vectorizer.pkl"))


# ============================
# Recommendation Engine
# ============================

def generate_recommendation(disease, risk_level):
    if disease == "Diabetes":
        if risk_level == "High":
            return "Strict sugar control required. Avoid refined carbs, exercise daily, consult endocrinologist."
        elif risk_level == "Moderate":
            return "Reduce sugar intake and monitor glucose weekly."
        else:
            return "Maintain balanced diet and regular activity."

    if disease == "Heart Disease":
        if risk_level == "High":
            return "Immediate cardiac evaluation recommended. Reduce cholesterol and stop smoking."
        elif risk_level == "Moderate":
            return "Monitor cholesterol and BP regularly."
        else:
            return "Maintain healthy lifestyle."

    if disease == "Stroke":
        if risk_level == "High":
            return "Control BP immediately and consult neurologist."
        elif risk_level == "Moderate":
            return "Monitor BP and glucose."
        else:
            return "Maintain regular health checkups."

    if disease == "Hypertension":
        return "Reduce salt intake, manage stress, and monitor BP daily."

    if disease == "Kidney Disease":
        return "Maintain hydration and control BP and sugar levels."

    return "Maintain healthy lifestyle."


# ============================
# OTP Email Function
# ============================

def send_otp_email(to_email, otp):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("EMAIL ERROR: EMAIL_USER or EMAIL_PASS not set.")
        return False

    subject = "HealthTrackk Email Verification OTP"
    body = f"""
Your OTP for verifying your HealthTrackk account is:

{otp}

This OTP is valid for 5 minutes.
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("EMAIL ERROR:", e)
        return False


def build_health_record(form_data):
    height_cm = form_data.get("height_cm", type=float)
    weight_kg = form_data.get("weight_kg", type=float)
    bmi = None
    if height_cm and weight_kg and height_cm > 0:
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)

    return {
        "date": form_data.get("record_date") or datetime.now().strftime("%Y-%m-%d"),
        "heart_rate": form_data.get("heart_rate", type=int),
        "systolic_bp": form_data.get("systolic_bp", type=int),
        "diastolic_bp": form_data.get("diastolic_bp", type=int),
        "blood_sugar": form_data.get("blood_sugar", type=float),
        "temperature": form_data.get("temperature", type=float),
        "oxygen_level": form_data.get("oxygen_level", type=float),
        "bmi": bmi,
        "cholesterol": form_data.get("cholesterol", type=float),
        "hemoglobin": form_data.get("hemoglobin", type=float),
        "creatinine": form_data.get("creatinine", type=float),
        "tsh_level": form_data.get("tsh_level", type=float),
        "notes": (form_data.get("record_notes") or "").strip(),
    }


def upsert_user_profile(user_id, form_data):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET age = ?, gender = ?, height = ?, weight = ?
        WHERE user_id = ?
        """,
        (
            form_data.get("age", type=int),
            form_data.get("gender"),
            form_data.get("height", type=float),
            form_data.get("weight", type=float),
            user_id,
        ),
    )

    cursor.execute(
        """
        INSERT INTO user_profiles (
            user_id,
            blood_group,
            allergies,
            chronic_conditions,
            emergency_contact_name,
            emergency_contact_phone,
            primary_goal,
            city,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            blood_group = excluded.blood_group,
            allergies = excluded.allergies,
            chronic_conditions = excluded.chronic_conditions,
            emergency_contact_name = excluded.emergency_contact_name,
            emergency_contact_phone = excluded.emergency_contact_phone,
            primary_goal = excluded.primary_goal,
            city = excluded.city,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            (form_data.get("blood_group") or "").strip(),
            (form_data.get("allergies") or "").strip(),
            (form_data.get("chronic_conditions") or "").strip(),
            (form_data.get("emergency_contact_name") or "").strip(),
            (form_data.get("emergency_contact_phone") or "").strip(),
            (form_data.get("primary_goal") or "").strip(),
            (form_data.get("city") or "").strip(),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )

    conn.commit()
    conn.close()


def fetch_dashboard_context(user_id):
    conn = get_db()
    cursor = conn.cursor()

    predictions = cursor.execute(
        """
        SELECT disease_name, probability, risk_level, prediction_date
        FROM predictions
        WHERE user_id = ?
        ORDER BY prediction_date DESC
        """,
        (user_id,),
    ).fetchall()

    recent_records = cursor.execute(
        """
        SELECT *
        FROM health_records
        WHERE user_id = ?
        ORDER BY date DESC, record_id DESC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()

    vaccinations = cursor.execute(
        """
        SELECT *
        FROM vaccinations
        WHERE user_id = ?
        ORDER BY
            CASE status
                WHEN 'Scheduled' THEN 0
                WHEN 'Overdue' THEN 1
                ELSE 2
            END,
            COALESCE(due_date, administered_date) ASC,
            vaccination_id DESC
        LIMIT 8
        """,
        (user_id,),
    ).fetchall()

    profile = cursor.execute(
        """
        SELECT
            u.user_id,
            u.name,
            u.email,
            u.age,
            u.gender,
            u.height,
            u.weight,
            u.created_at,
            p.blood_group,
            p.allergies,
            p.chronic_conditions,
            p.emergency_contact_name,
            p.emergency_contact_phone,
            p.primary_goal,
            p.city,
            p.updated_at
        FROM users u
        LEFT JOIN user_profiles p ON p.user_id = u.user_id
        WHERE u.user_id = ?
        """,
        (user_id,),
    ).fetchone()

    symptom_history = cursor.execute(
        """
        SELECT predicted_disease, symptoms, created_at
        FROM symptom_assessments
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    chat_count = cursor.execute(
        "SELECT COUNT(*) AS total FROM chatbot_history WHERE user_id = ?",
        (user_id,),
    ).fetchone()["total"]

    conn.close()

    prediction_rows = [tuple(row) for row in predictions]
    recent_records = [row_to_dict(row) for row in recent_records]
    vaccinations = [row_to_dict(row) for row in vaccinations]
    profile = row_to_dict(profile)
    symptom_history = [row_to_dict(row) for row in symptom_history]

    avg_risk = (
        sum([row[1] for row in prediction_rows if row[1] is not None]) / len(prediction_rows)
        if prediction_rows
        else 0
    )
    health_score = max(10, int((1 - avg_risk) * 100)) if prediction_rows else 100
    upcoming_vaccines = sum(1 for item in vaccinations if item["status"] != "Completed")
    latest_record = recent_records[0] if recent_records else None

    return {
        "predictions": prediction_rows,
        "recent_records": recent_records,
        "vaccinations": vaccinations,
        "profile": profile,
        "symptom_history": symptom_history,
        "chat_count": chat_count,
        "health_score": health_score,
        "latest_record": latest_record,
        "upcoming_vaccines": upcoming_vaccines,
        "member_since": profile.get("created_at", ""),
    }


# ============================
# Login Required Decorator
# ============================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================
# Language Switch
# ============================

@app.route("/change-language/<lang>")
def change_language(lang):
    if lang in app.config["BABEL_SUPPORTED_LOCALES"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("home"))


# ============================
# HOME
# ============================

@app.route("/")
def home():
    return render_template("home.html")


# ============================
# LOGOUT
# ============================

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================
# CHATBOT (LOGIN PROTECTED)
# ============================
@app.route("/chatbot", methods=["GET"])
@login_required
def chatbot_page():
    return render_template("chatbot.html")
@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_message = request.form.get("message", "").lower()

    # 🔥 Knowledge base (expandable)
    knowledge_base = {

        # GENERAL
        "hello": "Hello! How can I help you with your health today?",
        "hi": "Hi there! Ask me anything about your health.",
        "how are you": "I'm here to help you stay healthy 😊",

        # FEVER
        "fever": "Fever is usually due to infection. Stay hydrated and rest. If it persists, consult a doctor.",
        "high fever": "High fever above 102°F needs medical attention.",
        "fever treatment": "Take rest, fluids, and paracetamol if needed.",

        # COLD / COUGH
        "cold": "Common cold is viral. Drink warm fluids and rest.",
        "cough": "Cough may be due to infection or allergy. Steam inhalation helps.",
        "dry cough": "Dry cough can be due to irritation. Stay hydrated.",

        # DIET
        "diet": "Eat balanced meals with protein, fruits, vegetables, and water.",
        "healthy food": "Include green vegetables, fruits, and whole grains.",
        "weight loss": "Reduce sugar, eat protein, and exercise daily.",

        # EXERCISE
        "exercise": "30 minutes daily exercise is recommended.",
        "gym": "Start with light workouts and increase gradually.",
        "yoga": "Yoga improves flexibility and reduces stress.",

        # HEART
        "heart": "Maintain low cholesterol, exercise regularly, and avoid smoking.",
        "heart disease": "Risk increases with poor lifestyle. Stay active and eat healthy.",

        # DIABETES
        "diabetes": "Control sugar intake, exercise daily, and monitor glucose.",
        "high sugar": "Avoid sweets and processed food.",

        # STRESS
        "stress": "Practice meditation, yoga, and take proper sleep.",
        "anxiety": "Deep breathing and relaxation help reduce anxiety.",

        # SLEEP
        "sleep": "Sleep at least 7-8 hours daily.",
        "insomnia": "Avoid screens before bed and maintain routine.",

        # WATER
        "water": "Drink 2-3 liters of water daily.",
        "hydration": "Stay hydrated especially in hot weather.",

        # IMMUNITY
        "immunity": "Eat fruits, vegetables, and exercise regularly.",
        "boost immunity": "Vitamin C, sleep, and exercise help.",

        # HEADACHE
        "headache": "Rest and hydration help. If frequent, consult doctor.",
        "migraine": "Avoid triggers like stress and bright light.",

        # STOMACH
        "stomach pain": "Could be indigestion. Avoid heavy food.",
        "acidity": "Avoid spicy food and eat on time.",

        # SKIN
        "skin": "Drink water and maintain hygiene.",
        "pimples": "Avoid oily food and keep skin clean.",

        # EMERGENCY
        "emergency": "Call ambulance (108 in India) immediately.",
        "chest pain": "Seek immediate medical help.",

        # DEFAULT
        "default": "I'm here to help with health questions. Try asking about fever, diet, exercise, or symptoms."
    }

    # 🔍 Matching logic
    # 🔍 Matching logic (FIXED)
    for key in knowledge_base:
     keywords = key.split()

    for word in keywords:
        if word in user_message:
            return jsonify({"bot": knowledge_base[key]})

# ✅ default fallback
        return jsonify({"bot": knowledge_base["default"]})
    
        
# ============================
# NEARBY HOSPITALS (ONLY ONE ROUTE)
# ============================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)


def build_hospital_query(lat, lon, radius=8000, include_relations=True):
    relation_block = f'\n          relation["amenity"="hospital"](around:{radius},{lat},{lon});' if include_relations else ""
    return f"""
        [out:json][timeout:20];
        (
          node["amenity"="hospital"](around:{radius},{lat},{lon});
          way["amenity"="hospital"](around:{radius},{lat},{lon});{relation_block}
        );
        out center tags;
    """


def fetch_overpass_hospitals(lat, lon):
    overpass_endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]

    queries = [
        build_hospital_query(lat, lon, radius=8000, include_relations=True),
        build_hospital_query(lat, lon, radius=5000, include_relations=False),
    ]

    headers = {
        "User-Agent": "HealthTrackk/1.0 (hospital lookup)",
        "Accept": "application/json",
    }

    errors = []

    for endpoint in overpass_endpoints:
        for query in queries:
            try:
                response = requests.get(
                    endpoint,
                    params={"data": query},
                    timeout=20,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                if data.get("elements"):
                    return data
                errors.append(f"{endpoint}: empty result")
            except requests.exceptions.RequestException as exc:
                errors.append(f"{endpoint}: {exc}")
            except ValueError as exc:
                errors.append(f"{endpoint}: invalid json ({exc})")

    raise requests.exceptions.RequestException("; ".join(errors))


import json as _json
from datetime import date

@app.route("/enroll-program", methods=["POST"])
def enroll_program():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data       = request.get_json() or request.form
    program_id = data.get("program_id")

    if not program_id:
        return jsonify({"success": False, "error": "program_id required"}), 400

    user_id = session["user_id"]
    conn    = get_db()

    program = conn.execute(
        "SELECT id, name FROM yoga_programs WHERE id = ?", (int(program_id),)
    ).fetchone()
    if not program:
        return jsonify({"success": False, "error": "Program not found"}), 404

    existing = conn.execute(
        "SELECT id FROM enrolled_programs WHERE user_id = ? AND program_id = ?",
        (user_id, int(program_id))
    ).fetchone()

    if existing:
        return jsonify({"success": True, "message": f"Already enrolled in {program['name']}!", "program_id": int(program_id)})

    conn.execute(
        "INSERT INTO enrolled_programs (user_id, program_id) VALUES (?, ?)",
        (user_id, int(program_id))
    )
    conn.commit()
    return jsonify({"success": True, "message": f"Enrolled in {program['name']}!", "program_id": int(program_id)}), 201




@app.route("/user-progress")
def user_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    user_id = session["user_id"]
    conn    = get_db()

    rows = conn.execute("""
        SELECT ep.program_id,
               yp.name          AS program_name,
               yp.duration_days,
               ep.start_date,
               COUNT(CASE WHEN up.completed = 1 THEN 1 END) AS completed_days
        FROM enrolled_programs ep
        JOIN yoga_programs yp ON yp.id = ep.program_id
        LEFT JOIN user_progress up
               ON up.user_id = ep.user_id AND up.program_id = ep.program_id
        WHERE ep.user_id = ?
        GROUP BY ep.program_id
    """, (user_id,)).fetchall()

    programs = []
    for r in rows:
        total = r["duration_days"]
        done  = r["completed_days"]
        programs.append({
            "program_id":     r["program_id"],
            "program_name":   r["program_name"],
            "start_date":     r["start_date"],
            "duration_days":  total,
            "completed_days": done,
            "percent":        round(done / total * 100) if total else 0,
        })

    return jsonify({"success": True, "programs": programs})

@app.route("/nearby-hospitals", methods=["POST"])
def nearby_hospitals():
    try:
        data = request.get_json(silent=True) or {}

        lat = data.get("lat")
        lon = data.get("lon")

        if lat is None or lon is None:
            return jsonify({
                "success": False,
                "message": "Location missing"
            }), 400

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid coordinates"
            }), 400

        overpass_data = fetch_overpass_hospitals(lat, lon)
        hospitals = []

        for element in overpass_data.get("elements", []):
            tags = element.get("tags", {})

            name = tags.get("name", "Unknown Hospital")

            if "lat" in element and "lon" in element:
                h_lat = element["lat"]
                h_lon = element["lon"]
            elif "center" in element:
                h_lat = element["center"]["lat"]
                h_lon = element["center"]["lon"]
            else:
                continue

            distance = calculate_distance(lat, lon, h_lat, h_lon)

            address_parts = [
                tags.get("addr:housename"),
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:suburb"),
                tags.get("addr:city"),
                tags.get("addr:state")
            ]
            address = ", ".join([x for x in address_parts if x]) or "Nearby location"

            phone = (
                tags.get("phone")
                or tags.get("contact:phone")
                or tags.get("mobile")
                or tags.get("contact:mobile")
                or "Not available"
            )

            doctor_name = (
                tags.get("doctor")
                or tags.get("contact:person")
                or tags.get("operator")
                or tags.get("operator:name")
                or "Not available"
            )

            website = tags.get("website") or tags.get("contact:website") or ""
            emergency = tags.get("emergency", "Not available")
            maps_url = f"https://www.google.com/maps?q={h_lat},{h_lon}"

            hospitals.append({
                "name": name,
                "address": address,
                "distance": distance,
                "doctor_name": doctor_name,
                "phone": phone,
                "emergency": emergency,
                "website": website,
                "maps_url": maps_url,
                "lat": h_lat,
                "lon": h_lon
            })

        hospitals = sorted(hospitals, key=lambda x: x["distance"])[:10]

        return jsonify({
            "success": True,
            "hospitals": hospitals
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "Hospital service timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as e:
        print("HOSPITAL REQUEST ERROR:", str(e))
        return jsonify({
            "success": False,
            "message": "Hospital lookup service is temporarily busy. Please try again in a moment."
        }), 502

    except Exception as e:
        print("HOSPITAL ERROR:", str(e))
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
# ============================
# REGISTER
# ============================
def get_wellness_suggestions(disease, risk):
    suggestions = {
        "diet": [],
        "exercise": [],
        "yoga": [],
        "warning": []
    }

    if disease == "Diabetes":
        suggestions["diet"] = [
            "Reduce sugar and refined carbs",
            "Eat balanced meals at regular times",
            "Increase fiber-rich foods"
        ]
        suggestions["exercise"] = [
            "20 to 30 minutes of daily walking",
            "Light stretching",
            "Gentle post-meal movement"
        ]
        suggestions["yoga"] = [
            "Anulom Vilom",
            "Tadasana",
            "Vrikshasana"
        ]

    elif disease == "Heart Disease":
        suggestions["diet"] = [
            "Reduce oily and high-salt food",
            "Choose lighter balanced meals",
            "Stay hydrated"
        ]
        suggestions["exercise"] = [
            "Short daily walks",
            "Gentle mobility exercises",
            "Avoid sudden heavy workouts"
        ]
        suggestions["yoga"] = [
            "Deep breathing",
            "Anulom Vilom",
            "Shavasana"
        ]

    elif disease == "Stroke":
        suggestions["diet"] = [
            "Eat low-salt balanced meals",
            "Stay hydrated",
            "Avoid processed foods"
        ]
        suggestions["exercise"] = [
            "Only light guided movement",
            "Avoid intense exercise",
            "Take doctor advice before any workout"
        ]
        suggestions["yoga"] = [
            "Deep breathing only",
            "Gentle seated stretching",
            "Relaxation exercises"
        ]

    else:
        suggestions["diet"] = [
            "Maintain a balanced diet",
            "Drink enough water",
            "Avoid excess junk food"
        ]
        suggestions["exercise"] = [
            "Daily walking",
            "Light stretching",
            "Regular movement"
        ]
        suggestions["yoga"] = [
            "Tadasana",
            "Deep breathing",
            "Light yoga"
        ]

    if risk == "High":
        suggestions["warning"] = [
            "Do not start intense exercise without medical advice",
            "Seek professional care if symptoms feel serious"
        ]
    elif risk == "Moderate":
        suggestions["warning"] = [
            "Prefer light exercise and monitor symptoms"
        ]
    else:
        suggestions["warning"] = [
            "Continue healthy habits regularly"
        ]

    return suggestions
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            flash("Email already exists. Try logging in instead.", "error")
            return render_template("register.html")

        otp = str(random.randint(100000, 999999))

        if not send_otp_email(email, otp):
            flash("Failed to send OTP. Please try again.", "error")
            return render_template("register.html")

        session["temp_user"] = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        }

        session["otp"] = otp

        return redirect(url_for("verify_otp"))

    return render_template("register.html")


# ============================
# SYMPTOM BASED ASSESSMENT
# ============================

@app.route("/symptom-assessment", methods=["GET", "POST"])
@login_required
def symptom_assessment():
    if request.method == "POST":
        age = request.form.get("age")
        sex = request.form.get("sex")
        symptoms = request.form.getlist("symptoms")

        bp = request.form.get("bp")
        sugar = request.form.get("sugar")
        smoking = request.form.get("smoking")
        exercise = request.form.get("exercise")
        family_history = request.form.get("family_history")
        stress = request.form.get("stress")

        if not age or not sex or not symptoms:
            return render_template(
                "symptom_assessment.html",
                error="Please fill all required fields."
            )

        age = int(age)

        scores = {
            "Heart Disease": 0,
            "Diabetes": 0,
            "Stroke": 0,
            "Hypertension": 0,
            "Kidney Disease": 0
        }

        # HEART DISEASE
        if "chest_pain" in symptoms:
            scores["Heart Disease"] += 3
        if "shortness_of_breath" in symptoms:
            scores["Heart Disease"] += 2
        if "palpitations" in symptoms:
            scores["Heart Disease"] += 2
        if "fatigue" in symptoms:
            scores["Heart Disease"] += 1
        if age > 50:
            scores["Heart Disease"] += 1
        if smoking == "yes":
            scores["Heart Disease"] += 2
        if family_history == "yes":
            scores["Heart Disease"] += 1
        if exercise == "no":
            scores["Heart Disease"] += 1

        # DIABETES
        if "frequent_urination" in symptoms:
            scores["Diabetes"] += 3
        if "increased_thirst" in symptoms:
            scores["Diabetes"] += 2
        if "weight_loss" in symptoms:
            scores["Diabetes"] += 2
        if "blurred_vision" in symptoms:
            scores["Diabetes"] += 2
        if age > 45:
            scores["Diabetes"] += 1
        if sugar == "high":
            scores["Diabetes"] += 3
        if family_history == "yes":
            scores["Diabetes"] += 1
        if exercise == "no":
            scores["Diabetes"] += 1

        # STROKE
        if "slurred_speech" in symptoms:
            scores["Stroke"] += 3
        if "one_side_weakness" in symptoms:
            scores["Stroke"] += 3
        if "severe_headache" in symptoms:
            scores["Stroke"] += 2
        if "dizziness" in symptoms:
            scores["Stroke"] += 2
        if age > 55:
            scores["Stroke"] += 1
        if bp == "high":
            scores["Stroke"] += 2
        if smoking == "yes":
            scores["Stroke"] += 1

        # HYPERTENSION
        if "headache" in symptoms:
            scores["Hypertension"] += 2
        if "dizziness" in symptoms:
            scores["Hypertension"] += 2
        if "high_blood_pressure" in symptoms:
            scores["Hypertension"] += 3
        if age > 40:
            scores["Hypertension"] += 1
        if bp == "high":
            scores["Hypertension"] += 3
        if stress == "high":
            scores["Hypertension"] += 1
        if smoking == "yes":
            scores["Hypertension"] += 1

        # KIDNEY DISEASE
        if "swelling" in symptoms:
            scores["Kidney Disease"] += 3
        if "back_pain" in symptoms:
            scores["Kidney Disease"] += 2
        if bp == "high":
            scores["Kidney Disease"] += 1
        if sugar == "high":
            scores["Kidney Disease"] += 1
        if age > 50:
            scores["Kidney Disease"] += 1

        predicted = max(scores, key=scores.get)
        predicted_score = scores[predicted]

        if predicted_score == 0:
            predicted = "General Health Check Recommended"

        if predicted_score >= 7:
            risk = "High"
        elif predicted_score >= 4:
            risk = "Moderate"
        else:
            risk = "Low"

        suggestions = get_wellness_suggestions(predicted, risk)

        confidence = min(0.95, round(scores[predicted] / 10, 2))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO symptom_assessments
            (user_id, age, sex, symptoms, predicted_disease)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            age,
            sex,
            ", ".join(symptoms),
            predicted
        ))

        cursor.execute(
            """
            INSERT INTO predictions (user_id, disease_name, probability, risk_level)
            VALUES (?, ?, ?, ?)
            """,
            (session["user_id"], predicted, confidence, risk),
        )

        conn.commit()
        conn.close()

        return render_template(
            "symptom_assessment.html",
            result=predicted,
            risk=risk,
            score=predicted_score,
            suggestions=suggestions,
            show_popup=True
        )

    return render_template("symptom_assessment.html")

# ============================
# VERIFY OTP
# ============================
@app.route("/fityoga")
@login_required
def fityoga():
    return render_template("fityoga.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if "temp_user" not in session:
        return redirect(url_for("register"))

    if request.method == "POST":
        user_otp = request.form["otp"]
        real_otp = session.get("otp")

        if user_otp == real_otp:
            user_data = session.get("temp_user")

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (name, email, password, is_verified)
                VALUES (?, ?, ?, 1)
            """, (user_data["name"], user_data["email"], user_data["password"]))

            conn.commit()
            conn.close()

            session.pop("temp_user", None)
            session.pop("otp", None)
            flash("Account verified. You can log in now.", "success")

            return redirect(url_for("login"))

        flash("Invalid OTP. Please try again.", "error")

    return render_template("verify_otp.html")

# ─────────────────────────────────────────────────────────────
# FITYOGA DASHBOARD DATA ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/fityoga-dashboard-data")
def fityoga_dashboard_data():
    """Returns all dynamic data for the FitYoga dashboard."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    user_id = session["user_id"]
    conn    = get_db()
    profile = conn.execute(
    "SELECT age, gender, height, weight FROM users WHERE user_id = ?",
    (user_id,)
).fetchone()

    # ── User basic info ───────────────────────────────────────
    user = conn.execute(
        "SELECT name, email FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    # ── Activity stats ────────────────────────────────────────
    # Count yoga sessions (enrolled programs progress entries)
    yoga_sessions = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND completed = 1",
        (user_id,)
    ).fetchone()[0]

    # Count enrolled programs
    enrolled_count = conn.execute(
        "SELECT COUNT(*) FROM enrolled_programs WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    # ── Streak calculation ────────────────────────────────────
    # Look at completed days ordered by date to find current streak
    streak = 0
    try:
        from datetime import date, timedelta
        today = date.today()
        streak = 0
        check_date = today
        for _ in range(365):
            day_str = str(check_date)
            done = conn.execute(
                """SELECT COUNT(*) FROM user_progress
                   WHERE user_id = ? AND completed = 1
                   AND completed_at LIKE ?""",
                (user_id, day_str + "%")
            ).fetchone()[0]
            if done > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
    except Exception:
        streak = 0

    # ── Weekly activity (last 7 days) ─────────────────────────
    from datetime import date, timedelta
    today = date.today()
    weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_label = d.strftime("%a")
        count = 0
        try:
            count = conn.execute(
                """SELECT COUNT(*) FROM user_progress
                   WHERE user_id = ? AND completed = 1
                   AND completed_at LIKE ?""",
                (user_id, str(d) + "%")
            ).fetchone()[0]
        except Exception:
            count = 0
        weekly.append({"day": day_label, "count": count})

    # ── Enrolled programs with progress ───────────────────────
    programs = []
    try:
        rows = conn.execute("""
            SELECT ep.program_id,
                   yp.name          AS program_name,
                   yp.duration_days,
                   ep.start_date,
                   COUNT(CASE WHEN up.completed = 1 THEN 1 END) AS completed_days
            FROM enrolled_programs ep
            JOIN yoga_programs yp ON yp.id = ep.program_id
            LEFT JOIN user_progress up
                   ON up.user_id = ep.user_id AND up.program_id = ep.program_id
            WHERE ep.user_id = ?
            GROUP BY ep.program_id
        """, (user_id,)).fetchall()

        for r in rows:
            total = r["duration_days"]
            done  = r["completed_days"]
            programs.append({
                "program_id":     r["program_id"],
                "program_name":   r["program_name"],
                "start_date":     r["start_date"],
                "duration_days":  total,
                "completed_days": done,
                "percent":        round(done / total * 100) if total else 0,
            })
    except Exception:
        programs = []

    # ── Water intake today ────────────────────────────────────
    water_today = 0
    try:
        from datetime import date
        water_row = conn.execute(
            "SELECT SUM(intake) FROM water_tracking WHERE user_id = ? AND date = ?",
            (user_id, str(date.today()))
        ).fetchone()[0]
        water_today = round(water_row or 0, 2)
    except Exception:
        water_today = 0

    return jsonify({
        "success": True,
        "data": {
            "user_name":      user["name"] if user else session.get("user_name", "User"),
            "yoga_sessions":  yoga_sessions,
            "enrolled_count": enrolled_count,
            "streak":         streak,
            "avg_score":      round(min(5.0, 3.5 + yoga_sessions * 0.02), 1),
            "active_days":    min(yoga_sessions + enrolled_count, 99),
            "weekly":         weekly,
            "programs":       programs,
            "water_today":    water_today,
            "age": profile["age"] if profile else None,
            "gender": profile["gender"] if profile else None,
            "height": profile["height"] if profile else None,
            "weight": profile["weight"] if profile else None,
        }
    })
@app.route("/fill")
@login_required
def fill():
    user_id = session["user_id"]

    data = fetch_dashboard_context(user_id)
    profile = data.get("profile", {})

    return render_template("fill.html", profile=profile)

@app.route("/save-profile", methods=["POST"])
@login_required
def save_profile():
    user_id = session["user_id"]

    upsert_user_profile(user_id, request.form)

    return redirect("/dashboard?tab=profile")   # 🔥 THIS LINE IS CRITICAL

@app.route("/log-water", methods=["POST"])
def log_water():
    """Log water intake. Body: { amount: 0.25 } in litres."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data   = request.get_json() or request.form
    amount = float(data.get("amount", 0.25))
    user_id = session["user_id"]

    from datetime import date
    today = str(date.today())
    conn  = get_db()

    try:
        # Create water_tracking table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS water_tracking (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                intake  REAL    DEFAULT 0.0,
                date    TEXT    DEFAULT (date('now'))
            )
        """)
        conn.execute(
            "INSERT INTO water_tracking (user_id, intake, date) VALUES (?,?,?)",
            (user_id, amount, today)
        )
        conn.commit()

        total = conn.execute(
            "SELECT SUM(intake) FROM water_tracking WHERE user_id=? AND date=?",
            (user_id, today)
        ).fetchone()[0] or 0

        return jsonify({
            "success": True,
            "total":   round(total, 2),
            "cups":    round(total / 0.25)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route("/mark-complete", methods=["POST"])
def mark_complete():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data       = request.get_json() or request.form
    program_id = data.get("program_id")
    day        = data.get("day")

    if not program_id or not day:
        return jsonify({"success": False, "error": "program_id and day required"}), 400

    user_id = session["user_id"]
    conn    = get_db()

    # Add completed_at column if it doesn't exist yet
    try:
        conn.execute("ALTER TABLE user_progress ADD COLUMN completed_at TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists

    enrolled = conn.execute(
        "SELECT id FROM enrolled_programs WHERE user_id=? AND program_id=?",
        (user_id, int(program_id))
    ).fetchone()
    if not enrolled:
        return jsonify({"success": False, "error": "Not enrolled"}), 403

    from datetime import datetime
    now = datetime.now().isoformat()

    existing = conn.execute(
        "SELECT id, completed FROM user_progress WHERE user_id=? AND program_id=? AND day_completed=?",
        (user_id, int(program_id), int(day))
    ).fetchone()

    if existing:
        new_val = 0 if existing["completed"] else 1
        completed_at = now if new_val else None
        conn.execute(
            "UPDATE user_progress SET completed=?, completed_at=? WHERE id=?",
            (new_val, completed_at, existing["id"])
        )
    else:
        new_val = 1
        conn.execute(
            """INSERT INTO user_progress
               (user_id, program_id, day_completed, completed, completed_at)
               VALUES (?,?,?,1,?)""",
            (user_id, int(program_id), int(day), now)
        )

    total_done = conn.execute(
        "SELECT COUNT(*) FROM user_progress WHERE user_id=? AND program_id=? AND completed=1",
        (user_id, int(program_id))
    ).fetchone()[0]

    conn.commit()
    return jsonify({
        "success":    True,
        "day":        int(day),
        "completed":  bool(new_val),
        "total_done": total_done
    })    
# ============================
# LOGIN
# ============================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ============================
# DASHBOARD
# ============================

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    tab = request.args.get("tab", "overview")
    user_id = session["user_id"]

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_profile":
            upsert_user_profile(user_id, request.form)
            session["user_name"] = request.form.get("name", session["user_name"]).strip() or session["user_name"]

            conn = get_db()
            conn.execute(
                "UPDATE users SET name = ? WHERE user_id = ?",
                (session["user_name"], user_id),
            )
            conn.commit()
            conn.close()
            flash("Profile updated.", "success")
            return redirect(url_for("dashboard", tab="profile"))

        if action == "add_record":
            record = build_health_record(request.form)
            conn = get_db()
            conn.execute(
                """
                INSERT INTO health_records (
                    user_id, date, heart_rate, systolic_bp, diastolic_bp,
                    blood_sugar, temperature, oxygen_level, bmi,
                    cholesterol, hemoglobin, creatinine, tsh_level, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    record["date"],
                    record["heart_rate"],
                    record["systolic_bp"],
                    record["diastolic_bp"],
                    record["blood_sugar"],
                    record["temperature"],
                    record["oxygen_level"],
                    record["bmi"],
                    record["cholesterol"],
                    record["hemoglobin"],
                    record["creatinine"],
                    record["tsh_level"],
                    record["notes"],
                ),
            )
            conn.commit()
            conn.close()
            flash("Health record added.", "success")
            return redirect(url_for("dashboard", tab="records"))

        if action == "add_vaccination":
            status = request.form.get("status") or "Scheduled"
            due_date = request.form.get("due_date") or ""
            if status == "Scheduled" and due_date:
                try:
                    if datetime.strptime(due_date, "%Y-%m-%d").date() < datetime.now().date():
                        status = "Overdue"
                except ValueError:
                    pass

            conn = get_db()
            conn.execute(
                """
                INSERT INTO vaccinations (
                    user_id, vaccine_name, dose_label, status, due_date,
                    administered_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    (request.form.get("vaccine_name") or "").strip(),
                    (request.form.get("dose_label") or "").strip(),
                    status,
                    due_date or None,
                    request.form.get("administered_date") or None,
                    (request.form.get("vaccination_notes") or "").strip(),
                ),
            )
            conn.commit()
            conn.close()
            flash("Vaccination entry saved.", "success")
            return redirect(url_for("dashboard", tab="vaccinations"))

    dashboard_data = fetch_dashboard_context(user_id)

    return render_template(
        "dashboard.html",
        active_tab=tab,
        **dashboard_data,
    )


# ============================
# RUN APP
# ============================
with app.app_context():
    init_fityoga_tables()
    seed_fityoga_data()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
