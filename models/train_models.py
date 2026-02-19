import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================
# 1. TRAIN DIABETES MODEL
# ============================

diabetes_path = os.path.join(BASE_DIR, "dataset", "diabetes.csv")
diabetes_df = pd.read_csv(diabetes_path)

X_diabetes = diabetes_df[['Glucose', 'BloodPressure', 'BMI', 'Age']]
y_diabetes = diabetes_df['Outcome']

X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(
    X_diabetes, y_diabetes, test_size=0.2, random_state=42
)

diabetes_model = RandomForestClassifier(n_estimators=100, random_state=42)
diabetes_model.fit(X_train_d, y_train_d)

accuracy_d = accuracy_score(y_test_d, diabetes_model.predict(X_test_d))
print("Diabetes Accuracy:", accuracy_d)

joblib.dump(diabetes_model, os.path.join(BASE_DIR, "models", "diabetes_model.pkl"))

# ============================
# 2. TRAIN HEART DISEASE MODEL
# ============================

heart_path = os.path.join(BASE_DIR, "dataset", "heart.csv")
heart_df = pd.read_csv(heart_path)

# Select important features
X_heart = heart_df[['age', 'trestbps', 'chol', 'thalach', 'oldpeak']]
y_heart = heart_df['target']

X_train_h, X_test_h, y_train_h, y_test_h = train_test_split(
    X_heart, y_heart, test_size=0.2, random_state=42
)

heart_model = RandomForestClassifier(n_estimators=100, random_state=42)
heart_model.fit(X_train_h, y_train_h)

accuracy_h = accuracy_score(y_test_h, heart_model.predict(X_test_h))
print("Heart Disease Accuracy:", accuracy_h)

joblib.dump(heart_model, os.path.join(BASE_DIR, "models", "heart_model.pkl"))
# ============================
# 3. TRAIN STROKE MODEL
# ============================

stroke_path = os.path.join(BASE_DIR, "dataset", "healthcare-dataset-stroke-data.csv")
stroke_df = pd.read_csv(stroke_path)

# Remove rows with missing BMI
stroke_df = stroke_df.dropna()

X_stroke = stroke_df[['age', 'hypertension', 'heart_disease', 'avg_glucose_level', 'bmi']]
y_stroke = stroke_df['stroke']

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X_stroke, y_stroke, test_size=0.2, random_state=42
)

stroke_model = RandomForestClassifier(n_estimators=100, random_state=42)
stroke_model.fit(X_train_s, y_train_s)

accuracy_s = accuracy_score(y_test_s, stroke_model.predict(X_test_s))
print("Stroke Accuracy:", accuracy_s)

joblib.dump(stroke_model, os.path.join(BASE_DIR, "models", "stroke_model.pkl"))


print("Models trained and saved successfully.")
