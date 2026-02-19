from translations_dict import TEXT
from flask import request
from flask_babel import Babel, _
import smtplib
import random
from email.mime.text import MIMEText
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import joblib
import numpy as np
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("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"),
    base_url="https://openrouter.ai/api/v1"
)



# ============================
# App Initialization
# ============================

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret_key_123"

app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'hi', 'mr']

def t(key):
    lang = session.get("lang", "en")
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))

@app.context_processor
def inject_translator():
    return dict(t=t)

babel = Babel()

def get_locale():
    return session.get('lang', 'en')

babel.init_app(app, locale_selector=get_locale)

# ============================
# Email Configuration
# ============================

EMAIL_ADDRESS = "healthtrackk.pvt.ltd@gmail.com"
EMAIL_PASSWORD = "cbrfnstiirrimzwm"

# ============================
# Paths
# ============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database", "health.db")

# ============================
# Load ML Models
# ============================

diabetes_model = joblib.load(os.path.join(BASE_DIR, "models", "diabetes_model.pkl"))
heart_model = joblib.load(os.path.join(BASE_DIR, "models", "heart_model.pkl"))
stroke_model = joblib.load(os.path.join(BASE_DIR, "models", "stroke_model.pkl"))
chatbot_model = joblib.load(os.path.join(BASE_DIR, "models", "chatbot_intent_model.pkl"))
vectorizer = joblib.load(os.path.join(BASE_DIR, "models", "chatbot_vectorizer.pkl"))

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
# HOME
# ============================

@app.route("/change-language/<lang>")
def change_language(lang):
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

@app.route("/")
def home():
    return render_template("home.html")

# ============================
# CHATBOT (LOGIN PROTECTED)
# ============================

@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":

        user_message = request.form.get("message")

        if not user_message:
            conn.close()
            return redirect("/chatbot")

        try:
            chat_completion = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional AI medical assistant.
Provide accurate health information.
Never provide dangerous medical instructions.
Always recommend consulting a doctor for serious conditions."""
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
            )

            response = chat_completion.choices[0].message.content

            if not response:
                response = "I couldn't generate a response. Please try again."

        except Exception as e:
            print("OPENROUTER ERROR:", str(e))
            response = "AI service is temporarily unavailable. Please try again later."

        cursor.execute("""
            INSERT INTO chatbot_history (user_id, user_message, bot_response)
            VALUES (?, ?, ?)
        """, (session["user_id"], user_message, response))

        conn.commit()
        conn.close()

        return redirect(url_for("chatbot"))

    # GET request
    cursor.execute("""
        SELECT user_message, bot_response
        FROM chatbot_history
        WHERE user_id = ?
        ORDER BY rowid ASC
    """, (session["user_id"],))

    chats = cursor.fetchall()
    conn.close()

    return render_template("chatbot.html", chats=chats)

# ============================
# REGISTER
# ============================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            return "Email already exists."

        otp = str(random.randint(100000, 999999))

        if not send_otp_email(email, otp):
            return "Failed to send OTP. Try again."

        session["temp_user"] = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        }

        session["otp"] = otp

        return redirect(url_for("verify_otp"))

    return render_template("register.html")

# ============================
# VERIFY OTP
# ============================

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if "temp_user" not in session:
        return redirect(url_for("register"))

    if request.method == "POST":

        user_otp = request.form["otp"]
        real_otp = session.get("otp")

        if user_otp == real_otp:

            user_data = session.get("temp_user")

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (name, email, password, is_verified)
                VALUES (?, ?, ?, 1)
            """, (user_data["name"], user_data["email"], user_data["password"]))

            conn.commit()
            conn.close()

            session.pop("temp_user", None)
            session.pop("otp", None)

            return redirect(url_for("login"))

        else:
            return "Invalid OTP"

    return render_template("verify_otp.html")

# ============================
# LOGIN
# ============================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")

# ============================
# DASHBOARD
# ============================

@app.route("/dashboard")
@login_required
def dashboard():

    tab = request.args.get("tab", "overview")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT disease_name, probability, risk_level 
    FROM predictions
    WHERE user_id = ?
    ORDER BY prediction_date DESC
    """, (session["user_id"],))

    predictions = cursor.fetchall()
    conn.close()

    if predictions:
        avg_risk = sum([p[1] for p in predictions]) / len(predictions)
        health_score = int((1 - avg_risk) * 100)
    else:
        health_score = 100

    return render_template(
        "dashboard.html",
        predictions=predictions,
        health_score=health_score,
        active_tab=tab
    )

# ============================

if __name__ == "__main__":
    app.run(debug=True)