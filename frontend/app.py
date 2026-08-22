import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ============================================================
# AYARLAR
# ============================================================
DEFAULT_API_URL = "http://127.0.0.1:8000/predict"
REQUEST_TIMEOUT = 10  # saniye

st.set_page_config(page_title="Churn Karar Destek Sistemi", layout="wide", page_icon="📊")

if "api_url" not in st.session_state:
    st.session_state["api_url"] = DEFAULT_API_URL


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================
def call_predict_api(payload: dict, timeout: int = REQUEST_TIMEOUT) -> tuple[Optional[dict], Optional[str]]:
    """
    API'ye tek bir müşteri için tahmin isteği gönderir.
    Streamlit UI çağrılarını (st.error vb.) İÇERMEZ, böylece thread-pool
    içinden de güvenle çağrılabilir. Sonuç: (veri, hata_mesajı) tuple'ı.
    """
    url = st.session_state.get("api_url", DEFAULT_API_URL)
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "API'ye bağlanılamadı. Backend sunucusunun (uvicorn) çalıştığından emin olun."
    except requests.exceptions.Timeout:
        return None, "İstek zaman aşımına uğradı. Backend yanıt vermiyor olabilir."
    except requests.exceptions.HTTPError:
        return None, f"API hatası (HTTP {response.status_code}): {response.text[:200]}"
    except Exception as e:
        return None, f"Beklenmeyen bir hata oluştu: {e}"


def to_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_payload_from_row(row: pd.Series) -> dict:
    """CSV'deki bir satırı API'nin beklediği JSON formatına dönüştürür (eksik/bozuk veriye toleranslı)."""

    def g(col, default=None):
        return row[col] if col in row and pd.notna(row[col]) else default

    senior_raw = g("SeniorCitizen", 0)
    try:
        senior = int(to_float(senior_raw))
    except (ValueError, TypeError):
        senior = 1 if str(senior_raw).strip().lower() in ("evet", "yes", "1", "true") else 0

    return {
        "gender": g("gender", "Female"),
        "SeniorCitizen": senior,
        "Partner": g("Partner", "No"),
        "Dependents": g("Dependents", "No"),
        "tenure": int(to_float(g("tenure", 0))),
        "PhoneService": g("PhoneService", "Yes"),
        "MultipleLines": g("MultipleLines", "No"),
        "InternetService": g("InternetService", "DSL"),
        "OnlineSecurity": g("OnlineSecurity", "No"),
        "OnlineBackup": g("OnlineBackup", "No"),
        "DeviceProtection": g("DeviceProtection", "No"),
        "TechSupport": g("TechSupport", "No"),
        "StreamingTV": g("StreamingTV", "No"),
        "StreamingMovies": g("StreamingMovies", "No"),
        "Contract": g("Contract", "Month-to-month"),
        "PaperlessBilling": g("PaperlessBilling", "Yes"),
        "PaymentMethod": g("PaymentMethod", "Electronic check"),
        "MonthlyCharges": to_float(g("MonthlyCharges", 0.0)),
        "TotalCharges": to_float(g("TotalCharges", 0.0)),
    }


def get_user_input() -> dict:
    """Sol menüden tekil müşteri bilgilerini toplar. Servis bağımlılıklarını (ör. internet yoksa
    'çevrimiçi güvenlik' seçilemez) otomatik tutarlı hale getirir."""
    with st.sidebar.expander("👤 Demografik Bilgiler", expanded=True):
        gender = st.selectbox("Cinsiyet", ["Female", "Male"])
        senior = st.selectbox("Yaşlı Mı?", ["Hayır", "Evet"])
        partner = st.selectbox("Partneri Var Mı?", ["Yes", "No"])
        dependents = st.selectbox("Bakmakla Yükümlü Olduğu Biri Var Mı?", ["Yes", "No"])

    with st.sidebar.expander("🌐 Alınan Hizmetler", expanded=False):
        phone_service = st.selectbox("Telefon Servisi", ["Yes", "No"])
        if phone_service == "No":
            multiple_lines = "No phone service"
            st.caption("ℹ️ Telefon servisi olmadığından 'Çoklu Hat' otomatik devre dışı.")
        else:
            multiple_lines = st.selectbox("Çoklu Hat", ["Yes", "No"])

        internet_service = st.selectbox("İnternet Servisi", ["DSL", "Fiber optic", "No"])
        if internet_service == "No":
            online_security = online_backup = device_protection = "No internet service"
            tech_support = streaming_tv = streaming_movies = "No internet service"
            st.caption("ℹ️ İnternet servisi olmadığından bağımlı hizmetler otomatik devre dışı.")
        else:
            online_security = st.selectbox("Çevrimiçi Güvenlik", ["Yes", "No"])
            online_backup = st.selectbox("Çevrimiçi Yedekleme", ["Yes", "No"])
            device_protection = st.selectbox("Cihaz Koruması", ["Yes", "No"])
            tech_support = st.selectbox("Teknik Destek", ["Yes", "No"])
            streaming_tv = st.selectbox("TV Yayını", ["Yes", "No"])
            streaming_movies = st.selectbox("Film Yayını", ["Yes", "No"])

    with st.sidebar.expander("💳 Sözleşme ve Fatura Detayları", expanded=False):
        tenure = st.number_input("Müşterilik Süresi (Ay)", min_value=0, max_value=100, value=1)
        contract = st.selectbox("Sözleşme Türü", ["Month-to-month", "One year", "Two year"])
        paperless_billing = st.selectbox("Kağıtsız Fatura", ["Yes", "No"])
        payment_method = st.selectbox("Ödeme Yöntemi", [
            "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"
        ])
        monthly_charges = st.number_input("Aylık Fatura ($)", min_value=0.0, value=70.70)
        total_charges = st.number_input("Toplam Harcama ($)", min_value=0.0, value=70.70)
        st.caption(f"💡 Referans tahmini (Aylık × Süre): ${monthly_charges * tenure:,.2f}")

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
        "TotalCharges": total_charges,
    }


def render_gauge(prob: float, is_risky: bool):
    """Terk olasılığını, rapordaki istek doğrultusunda bir 'hız sayacı' (gauge chart) olarak gösterir.
    plotly kurulu değilse (requirements.txt çalıştırılmadıysa) sessizce atlanır; yandaki
    st.progress zaten görsel geri bildirimi sağlıyor."""
    if not PLOTLY_AVAILABLE:
        st.caption("💡 Daha görsel bir hız sayacı için: `pip install plotly`")
        return

    bar_color = "#dc3545" if is_risky else "#198754"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=prob,
            number={"suffix": "%", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": bar_color, "thickness": 0.3},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 50], "color": "#e9f7ef"},
                    {"range": [50, 100], "color": "#fdecea"},
                ],
                "threshold": {
                    "line": {"color": "#212529", "width": 3},
                    "thickness": 0.85,
                    "value": 50,
                },
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=25, b=10))
    st.plotly_chart(fig, use_container_width=True)


def render_whatif_button(col, label: str, key: str, modifier_fn, base_prob: float):
    """Tek bir 'What-If' teklif butonunu render eder ve sonucu delta metrik olarak gösterir."""
    with col:
        if st.button(label, use_container_width=True, key=key):
            new_data = st.session_state["current_data"].copy()
            modifier_fn(new_data)
            with st.spinner("Simülasyon çalıştırılıyor..."):
                sim_result, err = call_predict_api(new_data)
            if err:
                st.error(f"⚠️ {err}")
            elif sim_result:
                new_prob = sim_result["churn_probability"]
                st.metric(
                    label="Bu teklif sonrası risk",
                    value=f"%{new_prob:.2f}",
                    delta=f"{new_prob - base_prob:.2f} puan",
                    delta_color="inverse",
                )


# ============================================================
# YAN MENÜ (NAVİGASYON)
# ============================================================
st.sidebar.title("📌 Menü")
sayfa = st.sidebar.radio("Gitmek İstediğiniz Sayfayı Seçin:", ["👤 Tekil Müşteri Analizi", "📁 Toplu Müşteri Analizi (CSV)"])

with st.sidebar.expander("⚙️ Gelişmiş Ayarlar", expanded=False):
    st.session_state["api_url"] = st.text_input("API Adresi", value=st.session_state["api_url"])
st.sidebar.caption(f"🔗 Bağlı API: `{st.session_state['api_url']}`")
st.sidebar.divider()


# ============================================================
# SAYFA 1: TEKİL MÜŞTERİ ANALİZİ
# ============================================================
if sayfa == "👤 Tekil Müşteri Analizi":
    st.title("📊 Müşteri Terk (Churn) Karar Destek Sistemi")
    st.markdown("Müşteri temsilcisi arayüzüne hoş geldiniz. Lütfen menüden müşteri bilgilerini girin.")

    st.sidebar.header("📋 Müşteri Bilgileri")
    user_data = get_user_input()

    col_run, col_reset = st.sidebar.columns(2)
    if col_run.button("🔍 Risk Analizi Yap", use_container_width=True):
        with st.spinner("Analiz yapılıyor..."):
            result, err = call_predict_api(user_data)
        if err:
            st.sidebar.error(f"⚠️ {err}")
        else:
            st.session_state["current_data"] = user_data
            st.session_state["result"] = result

    if col_reset.button("🔄 Temizle", use_container_width=True):
        st.session_state.pop("result", None)
        st.session_state.pop("current_data", None)
        st.rerun()

    if "result" in st.session_state:
        res = st.session_state["result"]
        prob = res.get("churn_probability", 0)
        status = res.get("risk_status", "")
        is_risky = res.get("churn_prediction") == 1

        st.divider()
        st.subheader("Bölüm 2: Risk Analiz Sonucu")

        if is_risky:
            st.error(f"🚨 **{status}**")
        else:
            st.success(f"✅ **{status}**")

        gcol1, gcol2 = st.columns([1, 1])
        with gcol1:
            render_gauge(prob, is_risky)
        with gcol2:
            st.metric(label="Müşterinin Terk Etme Olasılığı", value=f"%{prob:.2f}")
            st.progress(min(max(prob / 100, 0.0), 1.0))

        if is_risky:
            st.divider()
            st.subheader("💡 Bölüm 3: 'What-If' Simülatörü (Karar Destek)")
            st.info("Bu müşteri yüksek risk grubunda! Aşağıdaki tekliflerle riski nasıl düşürebileceğinizi simüle edin.")

            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)

            render_whatif_button(
                col1, "🎁 1 Yıllık Taahhüt Teklif Et", "sim_1yr",
                lambda d: d.__setitem__("Contract", "One year"), prob,
            )
            render_whatif_button(
                col2, "🎁 2 Yıllık Taahhüt Teklif Et", "sim_2yr",
                lambda d: d.__setitem__("Contract", "Two year"), prob,
            )
            render_whatif_button(
                col3, "💸 Aylık Faturada %15 İndirim Yap", "sim_discount",
                lambda d: d.__setitem__("MonthlyCharges", d["MonthlyCharges"] * 0.85), prob,
            )
            render_whatif_button(
                col4, "🚀 İnterneti Fiber Optik Yap", "sim_fiber",
                lambda d: d.__setitem__("InternetService", "Fiber optic"), prob,
            )
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


# ============================================================
# SAYFA 2: TOPLU MÜŞTERİ ANALİZİ (CSV)
# ============================================================
elif sayfa == "📁 Toplu Müşteri Analizi (CSV)":
    st.title("📁 Toplu Müşteri Churn Analizi")
    st.markdown("Müşteri veri tabanınızı yükleyerek toplu analiz gerçekleştirebilirsiniz.")

    uploaded_file = st.file_uploader("Lütfen CSV formatında müşteri listesi yükleyin:", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"CSV okunamadı: {e}")
            st.stop()

        st.subheader("📋 Müşteri Tablosu Önizleme")
        st.dataframe(df, use_container_width=True)
        st.info(f"Tabloda toplam **{len(df)}** müşteri kaydı bulundu.")

        max_workers = st.slider(
            "Paralel istek sayısı", 1, 10, 5,
            help="API'ye aynı anda gönderilecek istek sayısı. Yüksek değerler analizi hızlandırır fakat backend'i yorabilir.",
        )

        if st.button("🚀 Tüm Liste İçin Risk Analizi Başlat", type="primary", use_container_width=True):
            payloads = [build_payload_from_row(row) for _, row in df.iterrows()]
            results = [None] * len(payloads)
            errors = [None] * len(payloads)

            progress_bar = st.progress(0.0, text="Analiz başlatılıyor...")
            completed = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {executor.submit(call_predict_api, p): i for i, p in enumerate(payloads)}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    res, err = future.result()
                    results[idx] = res
                    errors[idx] = err
                    completed += 1
                    progress_bar.progress(completed / len(payloads), text=f"{completed}/{len(payloads)} müşteri analiz edildi...")
            progress_bar.empty()

            probs, preds, statuses = [], [], []
            for res, err in zip(results, errors):
                if res:
                    probs.append(res.get("churn_probability"))
                    preds.append(res.get("churn_prediction"))
                    statuses.append(res.get("risk_status"))
                else:
                    probs.append(None)
                    preds.append(None)
                    statuses.append(f"Hata: {err}")

            df_result = df.copy()
            df_result["Terk Olasılığı (%)"] = probs
            df_result["Risk Durumu"] = statuses
            df_result["Tahmin"] = preds
            st.session_state["batch_result"] = df_result

        if "batch_result" in st.session_state:
            df_result = st.session_state["batch_result"]
            st.divider()
            st.subheader("📊 Analiz Sonuçları")

            valid = df_result[df_result["Tahmin"].notna()]
            failed = len(df_result) - len(valid)
            high_risk_count = int((valid["Tahmin"] == 1).sum()) if len(valid) else 0
            avg_prob = valid["Terk Olasılığı (%)"].mean() if len(valid) else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Müşteri", len(df_result))
            c2.metric("Yüksek Riskli Müşteri", high_risk_count)
            c3.metric("Ortalama Terk Olasılığı", f"%{avg_prob:.2f}" if len(valid) else "N/A")

            if failed > 0:
                st.warning(f"⚠️ {failed} müşteri için analiz başarısız oldu (API/bağlantı hatası). Detaylar 'Risk Durumu' sütununda.")

            tab1, tab2 = st.tabs(["📋 Tüm Sonuçlar", "🚨 Yalnızca Yüksek Riskliler"])
            with tab1:
                st.dataframe(df_result, use_container_width=True)
            with tab2:
                st.dataframe(valid[valid["Tahmin"] == 1], use_container_width=True)

            if len(valid):
                st.subheader("📈 Risk Dağılımı")
                st.bar_chart(valid["Risk Durumu"].value_counts())

            csv_bytes = df_result.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Sonuçları CSV Olarak İndir",
                data=csv_bytes,
                file_name="churn_analiz_sonuclari.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info("Analiz başlatmak için lütfen bir CSV dosyası yükleyin.")