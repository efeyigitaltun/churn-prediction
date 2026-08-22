import streamlit as st
import requests
import pandas as pd

# API Ayarları
API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(page_title="Churn Karar Destek Sistemi", layout="wide", page_icon="📊")

# --- YAN MENÜ (NAVİGASYON) ---
st.sidebar.title("📌 Menü")
sayfa = st.sidebar.radio("Gitmek İstediğiniz Sayfayı Seçin:", ["👤 Tekil Müşteri Analizi", "📁 Toplu Müşteri Analizi (CSV)"])
st.sidebar.divider()

if sayfa == "👤 Tekil Müşteri Analizi":
    st.title("📊 Müşteri Terk (Churn) Karar Destek Sistemi")
    st.markdown("Müşteri temsilcisi arayüzüne hoş geldiniz. Lütfen menüden müşteri bilgilerini girin.")

    st.sidebar.header("📋 Müşteri Bilgileri")

    def get_user_input():
        with st.sidebar.expander("👤 Demografik Bilgiler", expanded=True):
            gender = st.selectbox("Cinsiyet", ["Female", "Male"])
            senior = st.selectbox("Yaşlı Mı?", ["Hayır", "Evet"])
            partner = st.selectbox("Partneri Var Mı?", ["Yes", "No"])
            dependents = st.selectbox("Bakmakla Yükümlü Olduğu Biri Var Mı?", ["Yes", "No"])

        with st.sidebar.expander("🌐 Alınan Hizmetler", expanded=False):
            phone_service = st.selectbox("Telefon Servisi", ["Yes", "No"])
            multiple_lines = st.selectbox("Çoklu Hat", ["Yes", "No", "No phone service"])
            internet_service = st.selectbox("İnternet Servisi", ["DSL", "Fiber optic", "No"])
            online_security = st.selectbox("Çevrimiçi Güvenlik", ["Yes", "No", "No internet service"])
            online_backup = st.selectbox("Çevrimiçi Yedekleme", ["Yes", "No", "No internet service"])
            device_protection = st.selectbox("Cihaz Koruması", ["Yes", "No", "No internet service"])
            tech_support = st.selectbox("Teknik Destek", ["Yes", "No", "No internet service"])
            streaming_tv = st.selectbox("TV Yayını", ["Yes", "No", "No internet service"])
            streaming_movies = st.selectbox("Film Yayını", ["Yes", "No", "No internet service"])

        with st.sidebar.expander("💳 Sözleşme ve Fatura Detayları", expanded=False):
            tenure = st.number_input("Müşterilik Süresi (Ay)", min_value=0, max_value=100, value=1)
            contract = st.selectbox("Sözleşme Türü", ["Month-to-month", "One year", "Two year"])
            paperless_billing = st.selectbox("Kağıtsız Fatura", ["Yes", "No"])
            payment_method = st.selectbox("Ödeme Yöntemi", [
                "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"
            ])
            monthly_charges = st.number_input("Aylık Fatura ($)", min_value=0.0, value=70.70)
            total_charges = st.number_input("Toplam Harcama ($)", min_value=0.0, value=70.70)

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

    def get_prediction(data):
        try:
            response = requests.post(API_URL, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"API Bağlantı Hatası: Lütfen backend sunucusunun açık olduğundan emin olun. Hata: {e}")
            return None

    if st.sidebar.button("🔍 Risk Analizi Yap", use_container_width=True):
        result = get_prediction(user_data)
        if result:
            st.session_state['current_data'] = user_data
            st.session_state['result'] = result

    if 'result' in st.session_state:
        res = st.session_state['result']
        prob = res.get('churn_probability', 0)
        status = res.get('risk_status', '')
        is_risky = res.get('churn_prediction') == 1

        st.divider()
        st.subheader("Bölüm 2: Risk Analiz Sonucu")
        
        if is_risky:
            st.error(f"🚨 **{status}**")
        else:
            st.success(f"✅ **{status}**")
            
        st.metric(label="Müşterinin Terk Etme Olasılığı", value=f"%{prob:.2f}")
        st.progress(prob / 100)

        if is_risky:
            st.divider()
            st.subheader("💡 Bölüm 3: 'What-If' Simülatörü (Karar Destek)")
            st.info("Bu müşteri yüksek risk grubunda! Aşağıdaki tekliflerle riski nasıl düşürebileceğinizi simüle edin.")
            
            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)
            
            with col1:
                if st.button("🎁 1 Yıllık Taahhüt Teklif Et", use_container_width=True):
                    new_data = st.session_state['current_data'].copy()
                    new_data['Contract'] = "One year"
                    sim_result = get_prediction(new_data)
                    if sim_result:
                        st.success(f"Sözleşmeyi **1 Yıllık** yaparsanız risk **%{prob:.2f}'den %{sim_result['churn_probability']:.2f}'ye** düşecektir.")
                        
            with col2:
                if st.button("🎁 2 Yıllık Taahhüt Teklif Et", use_container_width=True):
                    new_data = st.session_state['current_data'].copy()
                    new_data['Contract'] = "Two year"
                    sim_result = get_prediction(new_data)
                    if sim_result:
                        st.success(f"Sözleşmeyi **2 Yıllık** yaparsanız risk **%{prob:.2f}'den %{sim_result['churn_probability']:.2f}'ye** düşecektir.")

            with col3:
                if st.button("💸 Aylık Faturada %15 İndirim Yap", use_container_width=True):
                    new_data = st.session_state['current_data'].copy()
                    new_data['MonthlyCharges'] *= 0.85
                    sim_result = get_prediction(new_data)
                    if sim_result:
                        st.success(f"Faturada **%15 İndirim** yaparsanız risk **%{prob:.2f}'den %{sim_result['churn_probability']:.2f}'ye** düşecektir.")

            with col4:
                if st.button("🚀 İnterneti Fiber Optik Yap", use_container_width=True):
                    new_data = st.session_state['current_data'].copy()
                    new_data['InternetService'] = "Fiber optic"
                    sim_result = get_prediction(new_data)
                    if sim_result:
                        st.success(f"İnternet hizmetini **Fiber** yaparsanız risk **%{prob:.2f}'den %{sim_result['churn_probability']:.2f}'ye** düşecektir.")
    else:
        st.markdown("### 📌 Sistem Durumu")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🕒 Durum: Beklemede (Veri Girilmedi)")
        with col2:
            st.info("🔗 Bağlantı: API İstek İçin Hazır")
        with col3:
            st.success("🧠 Model: Hazır (LightGBM/XGBoost)")
        st.divider()
        st.warning("👈 Lütfen sol menüden müşteri parametrelerini belirleyip 'Risk Analizi Yap' butonuna tıklayın.")

# --- YENİ EKLENEN SAYFA: TOPLU ANALİZ ---
elif sayfa == "📁 Toplu Müşteri Analizi (CSV)":
    st.title("📁 Toplu Müşteri Churn Analizi")
    st.markdown("Müşteri veri tabanınızı yükleyerek toplu analiz gerçekleştirebilirsiniz.")
    
    uploaded_file = st.file_uploader("Lütfen CSV formatında müşteri listesi yükleyin:", type=["csv"])
    
    if uploaded_file is not None:
        # Dosyayı okuyup tablo haline getiriyoruz
        df = pd.read_csv(uploaded_file)
        
        st.subheader("📋 Müşteri Tablosu Önizleme")
        # Raporda istenilen "müşteri tablosu" bileşeni
        st.dataframe(df, use_container_width=True) 
        
        st.info(f"Tabloda toplam **{len(df)}** müşteri kaydı bulundu.")
        
        if st.button("🚀 Tüm Liste İçin Risk Analizi Başlat", type="primary", use_container_width=True):
            st.warning("Efe backend tarafında '/predict_batch' adlı yeni bir toplu analiz rotası oluşturduğunda bu buton aktif hale gelecektir. Arayüzümüz veri göndermeye tamamen hazırdır!")