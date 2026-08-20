import streamlit as st
import requests

# API Ayarları
API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(page_title="Churn Karar Destek Sistemi", layout="wide")

st.title("📊 Müşteri Terk (Churn) Karar Destek Sistemi")
st.markdown("Müşteri temsilcisi arayüzüne hoş geldiniz. Lütfen sol taraftaki menüden müşteri bilgilerini girin.")

# --- BÖLÜM 1: VERİ GİRİŞ FORMU (Sol Menü) ---
st.sidebar.header("Müşteri Bilgileri")

def get_user_input():
    gender = st.sidebar.selectbox("Cinsiyet", ["Female", "Male"])
    senior = st.sidebar.selectbox("Yaşlı Mı?", ["Hayır", "Evet"])
    partner = st.sidebar.selectbox("Partneri Var Mı?", ["Yes", "No"])
    dependents = st.sidebar.selectbox("Bakmakla Yükümlü Olduğu Biri Var Mı?", ["Yes", "No"])
    tenure = st.sidebar.number_input("Müşterilik Süresi (Ay)", min_value=0, max_value=100, value=1)
    
    phone_service = st.sidebar.selectbox("Telefon Servisi", ["Yes", "No"])
    multiple_lines = st.sidebar.selectbox("Çoklu Hat", ["Yes", "No", "No phone service"])
    
    internet_service = st.sidebar.selectbox("İnternet Servisi", ["DSL", "Fiber optic", "No"])
    online_security = st.sidebar.selectbox("Çevrimiçi Güvenlik", ["Yes", "No", "No internet service"])
    online_backup = st.sidebar.selectbox("Çevrimiçi Yedekleme", ["Yes", "No", "No internet service"])
    device_protection = st.sidebar.selectbox("Cihaz Koruması", ["Yes", "No", "No internet service"])
    tech_support = st.sidebar.selectbox("Teknik Destek", ["Yes", "No", "No internet service"])
    streaming_tv = st.sidebar.selectbox("TV Yayını", ["Yes", "No", "No internet service"])
    streaming_movies = st.sidebar.selectbox("Film Yayını", ["Yes", "No", "No internet service"])
    
    contract = st.sidebar.selectbox("Sözleşme Türü", ["Month-to-month", "One year", "Two year"])
    paperless_billing = st.sidebar.selectbox("Kağıtsız Fatura", ["Yes", "No"])
    payment_method = st.sidebar.selectbox("Ödeme Yöntemi", [
        "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"
    ])
    
    monthly_charges = st.sidebar.number_input("Aylık Fatura ($)", min_value=0.0, value=70.70)
    total_charges = st.sidebar.number_input("Toplam Harcama ($)", min_value=0.0, value=70.70)

    # API'nin beklediği JSON formatına çevirme
    return {
        "gender": gender,
        "SeniorCitizen": 1 if senior == "Evet" else 0,
        "Partner": partner,
        "Dependents": dependents,
        "tenure": tenure,
        "PhoneService": phone_service,
        "MultipleLines": multiple_lines,
        "InternetService": internet_service,
        "OnlineSecurity": online_security,
        "OnlineBackup": online_backup,
        "DeviceProtection": device_protection,
        "TechSupport": tech_support,
        "StreamingTV": streaming_tv,
        "StreamingMovies": streaming_movies,
        "Contract": contract,
        "PaperlessBilling": paperless_billing,
        "PaymentMethod": payment_method,
        "MonthlyCharges": monthly_charges,
        "TotalCharges": total_charges
    }

user_data = get_user_input()

# API İstek Fonksiyonu
def get_prediction(data):
    try:
        response = requests.post(API_URL, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Bağlantı Hatası: Lütfen Efe'nin backend sunucusunun (127.0.0.1:8000) açık olduğundan emin olun. Hata: {e}")
        return None

# Butona basıldığında çalışacak mantık (Session State ile durumu koruyoruz)
if st.sidebar.button("🔍 Risk Analizi Yap", use_container_width=True):
    result = get_prediction(user_data)
    if result:
        st.session_state['current_data'] = user_data
        st.session_state['result'] = result

# --- BÖLÜM 2 & 3: DASHBOARD VE WHAT-IF SİMÜLATÖRÜ ---
if 'result' in st.session_state:
    res = st.session_state['result']
    prob = res.get('churn_probability', 0)
    status = res.get('risk_status', '')
    is_risky = res.get('churn_prediction') == 1

    st.divider()
    st.subheader("Bölüm 2: Risk Analiz Sonucu")
    
    # Dinamik Renk Teması
    if is_risky:
        st.error(f"🚨 **{status}**")
    else:
        st.success(f"✅ **{status}**")
        
    st.metric(label="Müşterinin Terk Etme Olasılığı", value=f"%{prob:.2f}")
    st.progress(prob / 100)

    # BÖLÜM 3: "What-If" Simülatörü
    if is_risky:
        st.divider()
        st.subheader("💡 Bölüm 3: 'What-If' Simülatörü (Karar Destek)")
        st.info("Bu müşteri yüksek risk grubunda! Aşağıdaki tekliflerle riski nasıl düşürebileceğinizi simüle edin.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎁 1 Yıllık Taahhüt Teklif Et", use_container_width=True):
                new_data = st.session_state['current_data'].copy()
                new_data['Contract'] = "One year"
                sim_result = get_prediction(new_data)
                
                if sim_result:
                    new_prob = sim_result['churn_probability']
                    st.success(f"Tebrikler! Müşteriye **1 Yıllık** sözleşme yaparsanız risk **%{prob:.2f}'den %{new_prob:.2f}'ye** düşecektir.")
                    
        with col2:
            if st.button("🎁 2 Yıllık Taahhüt Teklif Et", use_container_width=True):
                new_data = st.session_state['current_data'].copy()
                new_data['Contract'] = "Two year"
                sim_result = get_prediction(new_data)
                
                if sim_result:
                    new_prob = sim_result['churn_probability']
                    st.success(f"Mükemmel! Müşteriye **2 Yıllık** sözleşme yaparsanız risk **%{prob:.2f}'den %{new_prob:.2f}'ye** düşecektir.")