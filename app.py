from flask import Flask
import sqlite3
import os
import joblib
import numpy as np

app = Flask(__name__)

# ============================
# Database Configuration
# ============================

DATABASE = os.path.join("database", "health.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================
# Load ML Models
# ============================

MODEL_PATH = os.path.join("models", "diabetes_model.pkl")
diabetes_model = joblib.load(MODEL_PATH)

# ============================
# Routes
# ============================

@app.route("/")
def home():
    return "AI Powered Health Tracking System Running Successfully"

# ----------------------------
# Test Database Route
# ----------------------------

@app.route("/testdb")
def test_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return str(tables)

# ----------------------------
# Diabetes Prediction Route
# ----------------------------

@app.route("/predict_diabetes")
def predict_diabetes():
    # Sample values (temporary for testing)
    glucose = 140
    blood_pressure = 80
    bmi = 28
    age = 45

    input_data = np.array([[glucose, blood_pressure, bmi, age]])

    prediction = diabetes_model.predict(input_data)[0]
    probability = diabetes_model.predict_proba(input_data)[0][1]

    result = "Diabetic" if prediction == 1 else "Not Diabetic"

    return f"""
    <h2>Diabetes Prediction Result</h2>
    <p><strong>Status:</strong> {result}</p>
    <p><strong>Probability:</strong> {round(probability * 100, 2)}%</p>
    """

# ============================

if __name__ == "__main__":
    app.run(debug=True)
