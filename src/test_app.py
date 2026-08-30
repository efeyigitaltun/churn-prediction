from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

# 1. Başarılı İstek Testi (Doğru Veri)
def test_predict_endpoint_success():
    payload = {
        "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "No",
        "tenure": 1, "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "Fiber optic",
        "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No",
        "StreamingTV": "No", "StreamingMovies": "No", "Contract": "Month-to-month",
        "PaperlessBilling": "Yes", "PaymentMethod": "Electronic check",
        "MonthlyCharges": 70.70, "TotalCharges": 70.70
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert "churn_probability" in response.json()

# 2. Eksik Veri Testi (422 Unprocessable Entity - Çökme Kontrolü)
def test_predict_endpoint_missing_data():
    payload = {
        "gender": "Female" 
        # tenure, aylık ücret gibi kritik veriler bilerek gönderilmedi
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422