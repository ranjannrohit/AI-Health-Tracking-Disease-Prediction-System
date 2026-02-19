import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Training Data
data = {
    "text": [
        "what is diabetes",
        "how to control sugar",
        "symptoms of heart disease",
        "how to reduce cholesterol",
        "stroke symptoms",
        "normal blood pressure",
        "kidney disease causes"
    ],
    "intent": [
        "diabetes",
        "diabetes",
        "heart",
        "heart",
        "stroke",
        "bp",
        "kidney"
    ]
}

df = pd.DataFrame(data)

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df["text"])
y = df["intent"]

model = LogisticRegression()
model.fit(X, y)

joblib.dump(model, "models/chatbot_intent_model.pkl")
joblib.dump(vectorizer, "models/chatbot_vectorizer.pkl")

print("Chatbot AI model trained and saved.")
