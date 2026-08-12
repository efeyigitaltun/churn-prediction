from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
import os

# FastAPI uygulamasını başlatıyoruz
app = FastAPI(
    title="Telco Churn Prediction API",
    description="Müşteri terk riskini tahmin eden ve What-If simülasyonu sunan yapay zeka servisi",
    version="1.0"
)

# Modelin dosya yolunu belirleyip dışa aktardığımız joblib dosyasını yüklüyoruz
# Not: app.py src içinde çalışacağı için model bir üst klasördeki models klasöründedir.
model_path = os.path.join(os.path.dirname(__file__), '../models/churn_model_v1.0.joblib')
model = joblib.load(model_path)

# Arayüzden (Osman'ın sisteminden) gelecek verinin formatını (schema) belirliyoruz
class CustomerFeatures(BaseModel):
    gender: str
    SeniorCitizen: int
    Partner: str
    Dependents: str
    tenure: int
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float
    TotalCharges: float

@app.get("/")
def home():
    return {"message": "Telco Churn Prediction API aktif ve çalışıyor! 🚀"}

@app.post("/predict")
def predict_churn(customer: CustomerFeatures):
    # Gelen veriyi Pandas DataFrame'e çeviriyoruz (Modelimiz DataFrame bekliyor)
    input_data = pd.DataFrame([customer.dict()])
    
    # Model ile tahmin yapma (Olasılıkları alıyoruz)
    probability = model.predict_proba(input_data)[0][1]
    prediction = int(model.predict(input_data)[0])
    
    # Risk durumuna göre karar üretme
    risk_status = "Yüksek Riskli (Terk Edebilir)" if prediction == 1 else "Sadık Müşteri"
    
    return {
        "churn_prediction": prediction,
        "risk_status": risk_status,
        "churn_probability": round(float(probability) * 100, 2)
    }