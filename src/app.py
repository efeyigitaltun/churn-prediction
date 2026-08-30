from fastapi import FastAPI, Request
from pydantic import BaseModel
import joblib
import pandas as pd
import os
import logging

# --- Güvenlik (Rate Limiting) Paketleri ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Loglama Yapılandırması (Dosyaya Yazdırma)
logging.basicConfig(
    filename="api_requests.log",
    level=logging.INFO,
    format="%(asctime)s - %(client_ip)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# FastAPI uygulamasını başlatıyoruz
app = FastAPI(
    title="Telco Churn Prediction API",
    description="Müşteri terk riskini tahmin eden ve What-If simülasyonu sunan yapay zeka servisi",
    version="1.0.0"
)
# IP adresine göre hız sınırlandırıcıyı tanımla
limiter = Limiter(key_func=get_remote_address)
# Limiter'ı uygulamaya entegre et
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "gender": "Female",
                    "SeniorCitizen": 0,
                    "Partner": "Yes",
                    "Dependents": "No",
                    "tenure": 1,
                    "PhoneService": "Yes",
                    "MultipleLines": "No",
                    "InternetService": "Fiber optic",
                    "OnlineSecurity": "No",
                    "OnlineBackup": "No",
                    "DeviceProtection": "No",
                    "TechSupport": "No",
                    "StreamingTV": "No",
                    "StreamingMovies": "No",
                    "Contract": "Month-to-month",
                    "PaperlessBilling": "Yes",
                    "PaymentMethod": "Electronic check",
                    "MonthlyCharges": 70.70,
                    "TotalCharges": 70.70
                }
            ]
        }
    }

@app.get("/")
def home():
    return {"message": "Telco Churn Prediction API aktif ve çalışıyor! 🚀"}

@app.post("/predict")
@limiter.limit("5/minute")
def predict_churn(request: Request, customer: CustomerFeatures):
    # Gelen veriyi Pandas DataFrame'e çeviriyoruz
    # Pydantic V2 güncellemesi için dict() yerine model_dump() kullanıldı
    input_data = pd.DataFrame([customer.model_dump()])
    
    # Model ile tahmin yapma
    probability = float(model.predict_proba(input_data)[0][1])
    prediction = int(model.predict(input_data)[0])
    
    # Risk durumuna göre karar üretme
    risk_status = "Yüksek Riskli (Terk Edebilir)" if prediction == 1 else "Sadık Müşteri"
    churn_probability_percentage = round(probability * 100, 2)
    
    # --- LOGLAMA İŞLEMİ ---
    client_ip = request.client.host if request.client else "Bilinmeyen IP"
    log_message = f"Risk Analizi İstegi - Sonuc: {risk_status} - Olasilik: %{churn_probability_percentage}"
    logger.info(log_message, extra={"client_ip": client_ip})
    
    return {
        "churn_prediction": prediction,
        "risk_status": risk_status,
        "churn_probability": churn_probability_percentage
    }