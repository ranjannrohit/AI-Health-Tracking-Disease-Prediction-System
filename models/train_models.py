import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# =============================
# Paths
# =============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "diabetes.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "diabetes_model.pkl")

# =============================
# Load Dataset
# =============================
df = pd.read_csv(DATASET_PATH)

# Select important features only
X = df[['Glucose', 'BloodPressure', 'BMI', 'Age']]
y = df['Outcome']

# =============================
# Train-Test Split
# =============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# =============================
# Train Model
# =============================
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# =============================
# Evaluate Model
# =============================
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("Diabetes Model Accuracy:", accuracy)

# =============================
# Save Model
# =============================
joblib.dump(model, MODEL_PATH)
print("Model saved successfully as diabetes_model.pkl")
