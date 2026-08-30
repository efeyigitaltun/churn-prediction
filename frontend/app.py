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
DEFAULT_API_URL = "https://churn-prediction-api-vbld.onrender.com/predict"
REQUEST_TIMEOUT = 10
CHART_CONFIG    = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False}

st.set_page_config(
    page_title="Churn Karar Destek Sistemi",
    layout="wide", page_icon="📊",
    initial_sidebar_state="expanded",
)

for key, val in [("api_url", DEFAULT_API_URL), ("lang", "TR")]:
    if key not in st.session_state:
        st.session_state[key] = val

# ============================================================
# ÇEVİRİLER
# ============================================================
T = {
    "TR": {
        "app_sub": "Karar Destek Sistemi",
        "backend_ok": "Sistem Aktif", "backend_fail": "Sistem Bağlantısı Yok",
        "sidebar_header": "📋 Müşteri Bilgileri",
        "analyze_btn": "🔍 Analiz Yap", "clear_btn": "🔄 Temizle",
        "demo": "👤 Demografik Bilgiler",
        "gender": "Cinsiyet", "gender_opts": ["Kadın", "Erkek"],
        "gender_map": {"Kadın": "Female", "Erkek": "Male"},
        "senior": "Yaşlı Mı?", "partner": "Partneri Var Mı?",
        "dependents": "Bakmakla Yükümlü Olduğu Biri Var Mı?",
        "yes_no": ["Evet", "Hayır"], "yn_map": {"Evet": "Yes", "Hayır": "No"},
        "services": "🌐 Alınan Hizmetler",
        "phone": "Telefon Servisi", "multiline": "Çoklu Hat",
        "no_phone_info": "ℹ️ Telefon servisi olmadığından 'Çoklu Hat' otomatik devre dışı.",
        "internet": "İnternet Servisi",
        "internet_opts": {"DSL": "DSL", "Fiber Optik": "Fiber optic", "Yok": "No"},
        "no_internet_info": "ℹ️ İnternet servisi olmadığından bağımlı hizmetler otomatik devre dışı.",
        "security": "Çevrimiçi Güvenlik", "backup": "Çevrimiçi Yedekleme",
        "device": "Cihaz Koruması", "techsupport": "Teknik Destek",
        "tv": "TV Yayını", "movies": "Film Yayını",
        "contract_sec": "💳 Sözleşme & Fatura", "tenure": "Müşterilik Süresi (Ay)",
        "contract": "Sözleşme Türü",
        "contract_opts": {"Aylık": "Month-to-month", "1 Yıllık": "One year", "2 Yıllık": "Two year"},
        "billing": "Kağıtsız Fatura", "payment": "Ödeme Yöntemi",
        "payment_opts": {
            "Elektronik Çek": "Electronic check", "Posta Çeki": "Mailed check",
            "Otomatik Banka Transferi": "Bank transfer (automatic)",
            "Otomatik Kredi Kartı": "Credit card (automatic)",
        },
        "monthly": "Aylık Fatura ($)", "total": "Toplam Harcama ($)",
        "ref_hint": "💡 Referans tahmini (Aylık × Süre)",
        "hero_badge": "🤖 AI Destekli · Gerçek Zamanlı",
        "hero_title": "Müşteri Terk (Churn) Karar Destek Sistemi",
        "hero_sub": "Tekil müşteri risk analizi ve toplu CSV analizi için entegre karar destek platformu.",
        "tab1": "👤 Tekil Müşteri", "tab2": "📁 Toplu Analiz (CSV)",
        "result_label": "Risk Analiz Sonucu", "prob_metric": "Terk Etme Olasılığı",
        "risky_sub": "Bu müşteri için acil aksiyon önerilir. Aşağıdan simülatörü kullanın.",
        "safe_sub": "Müşteri sadık görünüyor. Mevcut hizmet kalitesini koruyun.",
        "risk_low": "Düşük Risk", "risk_medium": "Orta Risk",
        "risk_high": "Yüksek Risk", "risk_critical": "Kritik Risk",
        "profile_title": "👤 Müşteri Profili",
        "profile_fields": ["Cinsiyet", "Yaş Grubu", "Müşterilik", "Sözleşme",
                           "İnternet", "Aylık Fatura", "Ödeme", "Partner"],
        "senior_yes": "Yaşlı (65+)", "senior_no": "Standart",
        "gender_disp": {"Female": "Kadın", "Male": "Erkek"},
        "internet_disp": {"DSL": "DSL", "Fiber optic": "Fiber Optik", "No": "Yok"},
        "partner_disp": {"Yes": "Var", "No": "Yok"}, "tenure_unit": "ay",
        "shap_title": "📊 Risk Faktörleri Analizi",
        "shap_increase": "🔴 Riski Artırıyor", "shap_decrease": "🟢 Riski Azaltıyor",
        "shap_xaxis": "Katkı Puanı",
        "shap_feat": {
            "Sözleşme Türü": "Sözleşme Türü", "Müşterilik Süresi": "Müşterilik Süresi",
            "İnternet Servisi": "İnternet Servisi", "Aylık Fatura": "Aylık Fatura",
            "Çevrimiçi Güvenlik": "Çevrimiçi Güvenlik", "Teknik Destek": "Teknik Destek",
            "Ödeme Yöntemi": "Ödeme Yöntemi", "Kağıtsız Fatura": "Kağıtsız Fatura",
            "Yaş Grubu": "Yaş Grubu", "Aile/Sosyal Bağ": "Aile/Sosyal Bağ",
        },
        "whatif_title": "💡 What-If Simülatörü — Müşteriyi Elde Tutma",
        "whatif_info": "Farklı senaryoları karşılaştırarak riski en çok azaltan seçeneği görebilirsiniz.",
        "whatif_btn": "🔄 Tüm Senaryoları Karşılaştır",
        "whatif_spinner": "Senaryolar karşılaştırılıyor...",
        "whatif_scenarios": {
            "Mevcut Durum": None, "1 Yıllık Taahhüt": {"Contract": "One year"},
            "2 Yıllık Taahhüt": {"Contract": "Two year"},
            "%15 Fatura İndirimi": "discount", "Fiber Optik": {"InternetService": "Fiber optic"},
        },
        "whatif_cols": ["Senaryo", "Risk (%)", "Değişim", "Risk Seviyesi"],
        "whatif_success": lambda n, b, nw, d: f"🎉 En iyi senaryo: **{n}** — Risk **%{b:.1f}'den %{nw:.1f}'e düşüyor!** ({d:.1f} puan iyileşme)",
        "whatif_info2": lambda n, b, nw: f"💡 En iyi senaryo: **{n}** — Risk %{b:.1f}'den %{nw:.1f}'e düşüyor.",
        "cta_title": "Analiz için müşteri bilgilerini girin",
        "cta_sub": "Sol menüden parametreleri belirleyip <strong>Analiz Yap</strong> butonuna tıklayın.",
        "batch_upload": "CSV formatında müşteri listesi yükleyin:",
        "batch_preview": "📋 Yüklenen Veri Önizleme",
        "batch_found": lambda n: f"Toplam **{n}** müşteri kaydı bulundu.",
        "batch_workers": "⚡ Paralel istek sayısı",
        "batch_start": "🚀 Tüm Liste İçin Risk Analizi Başlat",
        "batch_progress": lambda d, t: f"{d}/{t} müşteri analiz edildi...",
        "batch_results": "📊 Analiz Sonuçları",
        "batch_metrics": ["👥 Toplam Müşteri", "🚨 Yüksek Riskli", "✅ Sadık Müşteri", "📈 Ort. Terk Olasılığı"],
        "batch_failed": lambda n: f"⚠️ {n} müşteri için analiz başarısız.",
        "batch_viz": "📈 Risk Görselleştirme",
        "batch_donut_lbl": ["🚨 Yüksek Riskli", "✅ Sadık Müşteri"],
        "batch_donut_title": "Müşteri Risk Dağılımı",
        "batch_hist_title": "Risk Skoru Dağılımı",
        "batch_hist_xy": ["Terk Olasılığı (%)", "Müşteri Sayısı"],
        "batch_threshold": "Eşik (50%)",
        "batch_tabs": ["📋 Tüm Sonuçlar", "🚨 Yalnızca Yüksek Riskliler"],
        "batch_no_risky": "🎉 Yüksek riskli müşteri bulunamadı!",
        "batch_download": "⬇️ Sonuçları CSV Olarak İndir",
        "batch_empty_title": "CSV Dosyası Bekleniyor",
        "batch_empty_sub": "Yukarıdaki alandan bir CSV dosyası yükleyerek toplu analiz başlatabilirsiniz.",
        "gauge_title": "Terk Olasılığı", "gauge_delta": " puan (eşikten)",
    },
    "EN": {
        "app_sub": "Decision Support System",
        "backend_ok": "System Active", "backend_fail": "System Disconnected",
        "sidebar_header": "📋 Customer Information",
        "analyze_btn": "🔍 Analyze Risk", "clear_btn": "🔄 Clear",
        "demo": "👤 Demographics",
        "gender": "Gender", "gender_opts": ["Female", "Male"],
        "gender_map": {"Female": "Female", "Male": "Male"},
        "senior": "Senior Citizen?", "partner": "Has Partner?",
        "dependents": "Has Dependents?",
        "yes_no": ["Yes", "No"], "yn_map": {"Yes": "Yes", "No": "No"},
        "services": "🌐 Services",
        "phone": "Phone Service", "multiline": "Multiple Lines",
        "no_phone_info": "ℹ️ 'Multiple Lines' disabled — no phone service.",
        "internet": "Internet Service",
        "internet_opts": {"DSL": "DSL", "Fiber Optic": "Fiber optic", "None": "No"},
        "no_internet_info": "ℹ️ Internet-dependent services disabled.",
        "security": "Online Security", "backup": "Online Backup",
        "device": "Device Protection", "techsupport": "Tech Support",
        "tv": "Streaming TV", "movies": "Streaming Movies",
        "contract_sec": "💳 Contract & Billing", "tenure": "Tenure (Months)",
        "contract": "Contract Type",
        "contract_opts": {"Monthly": "Month-to-month", "1 Year": "One year", "2 Years": "Two year"},
        "billing": "Paperless Billing", "payment": "Payment Method",
        "payment_opts": {
            "Electronic Check": "Electronic check", "Mailed Check": "Mailed check",
            "Bank Transfer (Auto)": "Bank transfer (automatic)",
            "Credit Card (Auto)": "Credit card (automatic)",
        },
        "monthly": "Monthly Charges ($)", "total": "Total Charges ($)",
        "ref_hint": "💡 Reference estimate (Monthly × Tenure)",
        "hero_badge": "🤖 AI-Powered · Real-Time",
        "hero_title": "Customer Churn Decision Support System",
        "hero_sub": "Integrated decision support platform for single customer risk analysis and batch CSV analysis.",
        "tab1": "👤 Single Customer", "tab2": "📁 Batch Analysis (CSV)",
        "result_label": "Risk Analysis Result", "prob_metric": "Churn Probability",
        "risky_sub": "Immediate action required. Use the simulator below.",
        "safe_sub": "Customer appears loyal. Maintain service quality.",
        "risk_low": "Low Risk", "risk_medium": "Medium Risk",
        "risk_high": "High Risk", "risk_critical": "Critical Risk",
        "profile_title": "👤 Customer Profile",
        "profile_fields": ["Gender", "Age Group", "Tenure", "Contract",
                           "Internet", "Monthly Bill", "Payment", "Partner"],
        "senior_yes": "Senior (65+)", "senior_no": "Standard",
        "gender_disp": {"Female": "Female", "Male": "Male"},
        "internet_disp": {"DSL": "DSL", "Fiber optic": "Fiber Optic", "No": "None"},
        "partner_disp": {"Yes": "Yes", "No": "No"}, "tenure_unit": "months",
        "shap_title": "📊 Risk Factor Analysis",
        "shap_increase": "🔴 Increases Risk", "shap_decrease": "🟢 Decreases Risk",
        "shap_xaxis": "Contribution Score",
        "shap_feat": {
            "Sözleşme Türü": "Contract Type", "Müşterilik Süresi": "Tenure",
            "İnternet Servisi": "Internet Service", "Aylık Fatura": "Monthly Charges",
            "Çevrimiçi Güvenlik": "Online Security", "Teknik Destek": "Tech Support",
            "Ödeme Yöntemi": "Payment Method", "Kağıtsız Fatura": "Paperless Billing",
            "Yaş Grubu": "Age Group", "Aile/Sosyal Bağ": "Family Ties",
        },
        "whatif_title": "💡 What-If Simulator — Customer Retention",
        "whatif_info": "Compare the scenarios below to see which option reduces risk the most.",
        "whatif_btn": "🔄 Compare All Scenarios",
        "whatif_spinner": "Comparing scenarios...",
        "whatif_scenarios": {
            "Current Status": None, "1-Year Contract": {"Contract": "One year"},
            "2-Year Contract": {"Contract": "Two year"},
            "15% Bill Discount": "discount", "Fiber Optic Upgrade": {"InternetService": "Fiber optic"},
        },
        "whatif_cols": ["Scenario", "Risk (%)", "Change", "Risk Level"],
        "whatif_success": lambda n, b, nw, d: f"🎉 Best scenario: **{n}** — Risk drops from **{b:.1f}% to {nw:.1f}%!** ({d:.1f} point improvement)",
        "whatif_info2": lambda n, b, nw: f"💡 Best scenario: **{n}** — Risk drops to {nw:.1f}%.",
        "cta_title": "Enter customer details to start analysis",
        "cta_sub": "Set parameters from the left menu and click <strong>Analyze Risk</strong>.",
        "batch_upload": "Upload customer list in CSV format:",
        "batch_preview": "📋 Data Preview",
        "batch_found": lambda n: f"Found **{n}** customer records.",
        "batch_workers": "⚡ Parallel requests",
        "batch_start": "🚀 Start Risk Analysis for All",
        "batch_progress": lambda d, t: f"{d}/{t} customers analyzed...",
        "batch_results": "📊 Analysis Results",
        "batch_metrics": ["👥 Total Customers", "🚨 High Risk", "✅ Loyal Customers", "📈 Avg. Churn Prob."],
        "batch_failed": lambda n: f"⚠️ Analysis failed for {n} customers.",
        "batch_viz": "📈 Risk Visualization",
        "batch_donut_lbl": ["🚨 High Risk", "✅ Loyal"],
        "batch_donut_title": "Customer Risk Distribution",
        "batch_hist_title": "Risk Score Distribution",
        "batch_hist_xy": ["Churn Probability (%)", "Customer Count"],
        "batch_threshold": "Threshold (50%)",
        "batch_tabs": ["📋 All Results", "🚨 High Risk Only"],
        "batch_no_risky": "🎉 No high-risk customers found!",
        "batch_download": "⬇️ Download Results as CSV",
        "batch_empty_title": "Waiting for CSV File",
        "batch_empty_sub": "Upload a CSV file from the area above to start batch analysis.",
        "gauge_title": "Churn Probability", "gauge_delta": " points (from threshold)",
    }
}


# ============================================================
# ÖZEL CSS
# ============================================================
st.markdown(f"""
<style>
    .main .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}

    .hero-header {{
        background: linear-gradient(135deg, #003f6b 0%, #005b96 55%, #0077c2 100%);
        border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem;
        color: white; box-shadow: 0 6px 28px rgba(0,91,150,0.28);
    }}
    .hero-header h1 {{
        font-size: 1.85rem; font-weight: 800; margin: 0 0 0.45rem 0;
        letter-spacing: -0.4px; color: white !important;
    }}
    .hero-header p {{ font-size: 0.97rem; opacity: 0.88; margin: 0; }}
    .hero-badge {{
        display: inline-block; background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.3); border-radius: 50px;
        padding: 0.2rem 0.85rem; font-size: 0.75rem; margin-bottom: 0.75rem;
        letter-spacing: 0.6px; text-transform: uppercase; font-weight: 600;
    }}
    .logo-mark {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
        background: linear-gradient(135deg, #005b96 0%, #0077c2 100%);
        box-shadow: 0 3px 10px rgba(0,91,150,0.35);
    }}
    .logo-mark svg {{ width: 24px; height: 24px; }}
    .logo-mark.logo-mark-ghost {{
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.35);
        box-shadow: none;
    }}
    .hero-title-row {{ display: flex; align-items: center; gap: 0.9rem; }}
    .section-title {{
        font-size: 1.05rem; font-weight: 700; color: #1a2e44;
        margin: 0 0 1rem 0; padding-bottom: 0.4rem;
        border-bottom: 2px solid #005b96; display: inline-block;
    }}
    .summary-chip {{
        display: inline-block; background: #f0f4f8; border: 1px solid #dce3eb;
        border-radius: 8px; padding: 0.35rem 0.75rem; font-size: 0.82rem;
        margin: 0.2rem 0.15rem; color: #374151;
    }}
    .summary-chip b {{ color: #005b96; }}
    .cta-panel {{
        text-align: center; background: #f0f6ff; border-radius: 14px;
        padding: 2.5rem 2rem; border: 2px dashed #aac8e8; margin-top: 1rem;
    }}
    .empty-drop {{
        text-align: center; background: #f0f6ff; border-radius: 14px;
        padding: 3rem 2rem; border: 2px dashed #aac8e8; margin-top: 1rem;
    }}
    .empty-drop-icon  {{ font-size: 3rem; margin-bottom: 0.6rem; }}
    .empty-drop-title {{ font-size: 1.05rem; font-weight: 700; color: #1a2e44; margin-bottom: 0.35rem; }}
    .empty-drop-sub   {{ font-size: 0.88rem; color: #6c757d; }}
    [data-testid="metric-container"] {{
        background: white; border-radius: 12px; padding: 1rem 1.2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06); border: 1px solid #e9ecef;
    }}
    div[data-testid="stButton"] > button {{
        border-radius: 10px; font-weight: 600; transition: all 0.2s ease;
    }}
    div[data-testid="stButton"] > button:hover {{
        transform: translateY(-2px); box-shadow: 0 5px 14px rgba(0,0,0,0.14);
    }}
    section[data-testid="stSidebar"] {{ background: #f0f4f8; border-right: 2px solid #dce3eb; }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label {{
        font-size: 0.82rem; font-weight: 700; color: #374151;
    }}
    div[data-baseweb="select"] > div:first-child {{
        border: 1.5px solid #ced4da !important; border-radius: 8px !important;
        background-color: white !important; transition: border-color 0.2s, box-shadow 0.2s;
    }}
    div[data-baseweb="select"] > div:first-child:hover {{ border-color: #005b96 !important; }}
    div[data-baseweb="select"] > div:first-child:focus-within {{
        border-color: #005b96 !important; box-shadow: 0 0 0 3px rgba(0,91,150,0.15) !important;
    }}
    input[type="number"], input[type="text"] {{
        border: 1.5px solid #ced4da !important; border-radius: 8px !important;
    }}
    input[type="number"]:focus, input[type="text"]:focus {{
        border-color: #005b96 !important;
        box-shadow: 0 0 0 3px rgba(0,91,150,0.15) !important; outline: none !important;
    }}
    .stDataFrame {{ border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; background: #f0f4f8; border-radius: 10px; padding: 4px; }}
    .stTabs [data-baseweb="tab"] {{ border-radius: 8px; font-weight: 600; padding: 0.45rem 1.2rem; }}
    div[data-testid="stAlert"] {{ border-radius: 10px; }}
    .stProgress > div > div > div {{ border-radius: 50px; }}

    /* Mobile */
    @media (max-width: 640px) {{
        .hero-header {{ padding: 1.2rem 1.5rem; }}
        .hero-header h1 {{ font-size: 1.25rem; }}
        .hero-header p {{ font-size: 0.82rem; }}
        .main .block-container {{ padding-left: 0.5rem; padding-right: 0.5rem; }}
    }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================
def get_risk_level(prob: float, t: dict) -> tuple:
    if prob < 30:   return t["risk_low"],      "#198754", "🟢"
    elif prob < 60: return t["risk_medium"],   "#fd7e14", "🟡"
    elif prob < 80: return t["risk_high"],     "#e67e22", "🟠"
    else:           return t["risk_critical"], "#dc3545", "🔴"


def estimate_feature_contributions(data: dict) -> dict:
    c = {}
    c["Sözleşme Türü"] = {"Month-to-month": 28, "One year": -12, "Two year": -22}.get(data.get("Contract"), 0)
    tenure = int(data.get("tenure", 0))
    if   tenure <= 3:  c["Müşterilik Süresi"] = 24
    elif tenure <= 12: c["Müşterilik Süresi"] = 14
    elif tenure <= 36: c["Müşterilik Süresi"] = 2
    else:              c["Müşterilik Süresi"] = -20
    c["İnternet Servisi"] = {"Fiber optic": 15, "DSL": -5, "No": -12}.get(data.get("InternetService"), 0)
    mc = float(data.get("MonthlyCharges", 0))
    if   mc > 90: c["Aylık Fatura"] = 20
    elif mc > 70: c["Aylık Fatura"] = 12
    elif mc > 50: c["Aylık Fatura"] = 4
    else:         c["Aylık Fatura"] = -6
    c["Çevrimiçi Güvenlik"] = {"No": 10, "Yes": -8, "No internet service": -12}.get(data.get("OnlineSecurity"), 0)
    c["Teknik Destek"]      = {"No": 9,  "Yes": -7, "No internet service": -10}.get(data.get("TechSupport"), 0)
    if data.get("PaymentMethod") == "Electronic check": c["Ödeme Yöntemi"] = 11
    elif data.get("PaymentMethod") in ["Bank transfer (automatic)", "Credit card (automatic)"]: c["Ödeme Yöntemi"] = -5
    else: c["Ödeme Yöntemi"] = 0
    c["Kağıtsız Fatura"] = {"Yes": 5, "No": -3}.get(data.get("PaperlessBilling"), 0)
    c["Yaş Grubu"]       = 7 if data.get("SeniorCitizen") == 1 else -3
    has_p = data.get("Partner") == "Yes"; has_d = data.get("Dependents") == "Yes"
    c["Aile/Sosyal Bağ"] = 8 if (not has_p and not has_d) else (-5 if (has_p or has_d) else -9)
    return c


def check_api_health() -> bool:
    try:
        r = requests.get(st.session_state.get("api_url", DEFAULT_API_URL).replace("/predict", "/"), timeout=2)
        return r.status_code == 200
    except: return False


def call_predict_api(payload: dict, timeout: int = REQUEST_TIMEOUT):
    url = st.session_state.get("api_url", DEFAULT_API_URL)
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "API'ye bağlanılamadı."
    except requests.exceptions.Timeout:
        return None, "İstek zaman aşımına uğradı."
    except requests.exceptions.HTTPError:
        return None, f"API hatası (HTTP {r.status_code})"
    except Exception as e:
        return None, str(e)


def to_float(val, default=0.0):
    try: return float(val)
    except: return default


def build_payload_from_row(row: pd.Series) -> dict:
    def g(col, default=None):
        return row[col] if col in row and pd.notna(row[col]) else default
    sr = g("SeniorCitizen", 0)
    try: senior = int(to_float(sr))
    except: senior = 1 if str(sr).strip().lower() in ("evet","yes","1","true") else 0
    return {
        "gender": g("gender","Female"), "SeniorCitizen": senior,
        "Partner": g("Partner","No"), "Dependents": g("Dependents","No"),
        "tenure": int(to_float(g("tenure",0))), "PhoneService": g("PhoneService","Yes"),
        "MultipleLines": g("MultipleLines","No"), "InternetService": g("InternetService","DSL"),
        "OnlineSecurity": g("OnlineSecurity","No"), "OnlineBackup": g("OnlineBackup","No"),
        "DeviceProtection": g("DeviceProtection","No"), "TechSupport": g("TechSupport","No"),
        "StreamingTV": g("StreamingTV","No"), "StreamingMovies": g("StreamingMovies","No"),
        "Contract": g("Contract","Month-to-month"), "PaperlessBilling": g("PaperlessBilling","Yes"),
        "PaymentMethod": g("PaymentMethod","Electronic check"),
        "MonthlyCharges": to_float(g("MonthlyCharges",0.0)),
        "TotalCharges": to_float(g("TotalCharges",0.0)),
    }


def get_user_input(t: dict) -> dict:
    yn_map = t["yn_map"]

    with st.sidebar.expander(t["demo"], expanded=True):
        gender_tr  = st.selectbox(t["gender"], t["gender_opts"])
        senior_tr  = st.selectbox(t["senior"], t["yes_no"])
        partner_tr = st.selectbox(t["partner"], t["yes_no"])
        dep_tr     = st.selectbox(t["dependents"], t["yes_no"])

    with st.sidebar.expander(t["services"], expanded=False):
        phone_tr = st.selectbox(t["phone"], t["yes_no"])
        if yn_map[phone_tr] == "No":
            multiple_lines = "No phone service"
            st.caption(t["no_phone_info"])
        else:
            multi_tr       = st.selectbox(t["multiline"], t["yes_no"])
            multiple_lines = yn_map[multi_tr]

        internet_tr      = st.selectbox(t["internet"], list(t["internet_opts"].keys()))
        internet_service = t["internet_opts"][internet_tr]

        if internet_service == "No":
            online_security = online_backup = device_protection = "No internet service"
            tech_support = streaming_tv = streaming_movies      = "No internet service"
            st.caption(t["no_internet_info"])
        else:
            os_tr  = st.selectbox(t["security"],    t["yes_no"])
            ob_tr  = st.selectbox(t["backup"],      t["yes_no"])
            dp_tr  = st.selectbox(t["device"],      t["yes_no"])
            ts_tr  = st.selectbox(t["techsupport"], t["yes_no"])
            stv_tr = st.selectbox(t["tv"],          t["yes_no"])
            sm_tr  = st.selectbox(t["movies"],      t["yes_no"])
            online_security   = yn_map[os_tr];  online_backup     = yn_map[ob_tr]
            device_protection = yn_map[dp_tr];  tech_support      = yn_map[ts_tr]
            streaming_tv      = yn_map[stv_tr]; streaming_movies  = yn_map[sm_tr]

    with st.sidebar.expander(t["contract_sec"], expanded=False):
        tenure     = st.number_input(t["tenure"], min_value=0, max_value=100, value=1)
        contract_tr= st.selectbox(t["contract"], list(t["contract_opts"].keys()))
        pb_tr      = st.selectbox(t["billing"], t["yes_no"])
        payment_tr = st.selectbox(t["payment"], list(t["payment_opts"].keys()))
        monthly_charges = st.number_input(t["monthly"], min_value=0.0, value=70.70)
        total_charges   = st.number_input(t["total"],   min_value=0.0, value=70.70)
        st.caption(f"{t['ref_hint']}: ${monthly_charges * tenure:,.2f}")

    return {
        "gender": t["gender_map"][gender_tr],
        "SeniorCitizen": 1 if yn_map[senior_tr] == "Yes" else 0,
        "Partner": yn_map[partner_tr], "Dependents": yn_map[dep_tr],
        "tenure": tenure, "PhoneService": yn_map[phone_tr],
        "MultipleLines": multiple_lines, "InternetService": internet_service,
        "OnlineSecurity": online_security, "OnlineBackup": online_backup,
        "DeviceProtection": device_protection, "TechSupport": tech_support,
        "StreamingTV": streaming_tv, "StreamingMovies": streaming_movies,
        "Contract": t["contract_opts"][contract_tr],
        "PaperlessBilling": yn_map[pb_tr],
        "PaymentMethod": t["payment_opts"][payment_tr],
        "MonthlyCharges": monthly_charges, "TotalCharges": total_charges,
    }


def render_gauge(prob: float, level_color: str, t: dict):
    if not PLOTLY_AVAILABLE: return
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=prob,
        number={"suffix": "%", "font": {"size": 44, "color": level_color, "family": "sans-serif"}},
        delta={"reference": 50, "suffix": t["gauge_delta"], "font": {"size": 13},
               "increasing": {"color": "#dc3545"}, "decreasing": {"color": "#198754"}},
        title={"text": t["gauge_title"], "font": {"size": 13, "color": "#6c757d"}},
        gauge={
            "axis": {"range": [0,100], "tickwidth": 1, "tickcolor": "#adb5bd",
                     "tickfont": {"size": 10}, "nticks": 6},
            "bar": {"color": level_color, "thickness": 0.22},
            "bgcolor": "white", "borderwidth": 0,
            "steps": [
                {"range": [0,  30],  "color": "#d4edda"},
                {"range": [30, 60],  "color": "#fff3cd"},
                {"range": [60, 80],  "color": "#ffe5cc"},
                {"range": [80, 100], "color": "#f8d7da"},
            ],
            "threshold": {"line": {"color": "#212529", "width": 3}, "thickness": 0.80, "value": 50},
        },
    ))
    fig.update_layout(
        height=270, margin=dict(l=25,r=25,t=35,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "sans-serif"}, dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def render_shap_chart(data: dict, t: dict):
    if not PLOTLY_AVAILABLE: return
    contributions = estimate_feature_contributions(data)
    sorted_items  = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
    features_tr   = [t["shap_feat"].get(i[0], i[0]) for i in reversed(sorted_items)]
    values        = [i[1] for i in reversed(sorted_items)]
    colors        = ["#e53e3e" if v > 0 else "#2d8c4e" for v in values]
    text          = [f"+{v}" if v > 0 else str(v) for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=features_tr, orientation="h",
        marker_color=colors, marker_line=dict(color="white", width=0),
        text=text, textposition="outside", textfont=dict(size=11), cliponaxis=False,
    ))
    fig.add_vline(x=0, line_color="#6c757d", line_width=1.5)

    # Paper koordinatlarıyla sabit annotation (kaymıyor!)
    fig.add_annotation(
        x=0.98, y=-0.12, xref="paper", yref="paper", xanchor="right",
        text=t["shap_increase"], showarrow=False, font=dict(size=10, color="#e53e3e")
    )
    fig.add_annotation(
        x=0.02, y=-0.12, xref="paper", yref="paper", xanchor="left",
        text=t["shap_decrease"], showarrow=False, font=dict(size=10, color="#2d8c4e")
    )
    fig.update_layout(
        title=dict(text=t["shap_title"], font=dict(size=13, color="#1a2e44"), x=0),
        xaxis=dict(title=t["shap_xaxis"], showgrid=True, gridcolor="#f0f4f8",
                   zeroline=False, tickfont=dict(size=10), fixedrange=True),
        yaxis=dict(showgrid=False, tickfont=dict(size=11), fixedrange=True),
        height=340, margin=dict(l=10,r=70,t=45,b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, font=dict(family="sans-serif"), dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def render_customer_profile_card(data: dict, prob: float, t: dict):
    level_name, level_color, level_icon = get_risk_level(prob, t)
    internet_tr = t["internet_disp"].get(data.get("InternetService",""), data.get("InternetService",""))
    fields = t["profile_fields"]
    vals = [
        t["gender_disp"].get(data.get("gender",""), data.get("gender","")),
        t["senior_yes"] if data.get("SeniorCitizen") else t["senior_no"],
        f"{data.get('tenure',0)} {t['tenure_unit']}",
        data.get("Contract","—"),
        internet_tr,
        f"${data.get('MonthlyCharges',0):.2f}",
        data.get("PaymentMethod","—"),
        t["partner_disp"].get(data.get("Partner",""), "—"),
    ]
    rows_html = "".join([
        f'<div><div style="color:#6c757d;font-size:0.72rem;">{f}</div>'
        f'<b style="font-size:0.83rem;">{v}</b></div>'
        for f, v in zip(fields, vals)
    ])
    st.markdown(f"""
    <div style="background:white;border-radius:12px;padding:1.2rem 1.4rem;
                border:1px solid #e9ecef;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.8px;color:#6c757d;margin-bottom:0.8rem;">{t['profile_title']}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem 1rem;">{rows_html}</div>
        <div style="margin-top:0.9rem;padding-top:0.7rem;border-top:1px solid #f0f0f0;">
            <span style="background:{level_color}18;color:{level_color};
                         border:1.5px solid {level_color};border-radius:50px;
                         padding:0.25rem 0.9rem;font-size:0.8rem;font-weight:700;">
                {level_icon} {level_name}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_whatif_table(base_data: dict, base_prob: float, t: dict):
    if st.button(t["whatif_btn"], type="primary", use_container_width=True, key="whatif_all"):
        scenario_probs = {list(t["whatif_scenarios"].keys())[0]: base_prob}
        with st.spinner(t["whatif_spinner"]):
            payloads = {}
            for name, mod in t["whatif_scenarios"].items():
                if mod is None: continue
                new_data = {**base_data, **({"MonthlyCharges": base_data.get("MonthlyCharges",0)*0.85} if mod == "discount" else mod)}
                payloads[name] = new_data
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(call_predict_api, d): n for n, d in payloads.items()}
                for future in as_completed(futures):
                    name = futures[future]
                    res, _ = future.result()
                    scenario_probs[name] = res["churn_probability"] if res else None
        rows = []
        for name in t["whatif_scenarios"]:
            prob = scenario_probs.get(name)
            if prob is None: continue
            level_name, _, level_icon = get_risk_level(prob, t)
            rows.append({
                t["whatif_cols"][0]: name,
                t["whatif_cols"][1]: round(prob, 1),
                t["whatif_cols"][2]: round(prob - base_prob, 1),
                t["whatif_cols"][3]: f"{level_icon} {level_name}",
            })
        st.session_state["whatif_table"]   = rows
        st.session_state["balloons_shown"] = False

    if "whatif_table" in st.session_state:
        rows     = st.session_state["whatif_table"]
        df       = pd.DataFrame(rows)
        base_key = list(t["whatif_scenarios"].keys())[0]
        non_base = df[df[t["whatif_cols"][0]] != base_key]
        if len(non_base):
            best     = non_base.loc[non_base[t["whatif_cols"][1]].idxmin()]
            diff_pct = base_prob - best[t["whatif_cols"][1]]
            if diff_pct >= base_prob * 0.3 and not st.session_state.get("balloons_shown", False):
                st.success(t["whatif_success"](best[t["whatif_cols"][0]], base_prob, best[t["whatif_cols"][1]], diff_pct))
                st.balloons()
                st.session_state["balloons_shown"] = True
            elif diff_pct > 0:
                st.info(t["whatif_info2"](best[t["whatif_cols"][0]], base_prob, best[t["whatif_cols"][1]]))
        st.dataframe(df, use_container_width=True, hide_index=True,
            column_config={
                t["whatif_cols"][1]: st.column_config.ProgressColumn(t["whatif_cols"][1], min_value=0, max_value=100, format="%.1f%%"),
                t["whatif_cols"][2]: st.column_config.NumberColumn(t["whatif_cols"][2], format="%.1f"),
            })


def render_batch_charts(valid_df: pd.DataFrame, high: int, low: int, t: dict):
    if not PLOTLY_AVAILABLE: return
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(data=[go.Pie(
            labels=t["batch_donut_lbl"], values=[high, low], hole=0.65,
            marker=dict(colors=["#dc3545","#198754"], line=dict(color="white",width=2)),
            textinfo="label+percent", textfont=dict(size=11),
            hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
        )])
        fig.update_layout(
            title=dict(text=t["batch_donut_title"], font=dict(size=13,color="#1a2e44"), x=0.5),
            height=300, margin=dict(l=10,r=10,t=40,b=20),
            paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            annotations=[dict(text=f"<b>{high+low}</b>", x=0.5, y=0.5, showarrow=False,
                              font=dict(size=20, color="#1a2e44"))],
            dragmode=False,
        )
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    with c2:
        probs = valid_df["Terk Olasılığı (%)"].dropna().tolist()
        fig2  = go.Figure(go.Histogram(
            x=probs, nbinsx=20, marker_color="#005b96",
            marker_line=dict(color="white", width=0.5),
            hovertemplate=f"{t['batch_hist_xy'][0]}: %{{x:.1f}}%<br>{t['batch_hist_xy'][1]}: %{{y}}<extra></extra>",
        ))
        fig2.add_vline(x=50, line_color="#dc3545", line_width=2, line_dash="dash",
                       annotation_text=t["batch_threshold"], annotation_position="top right",
                       annotation_font=dict(size=10, color="#dc3545"))
        fig2.update_layout(
            title=dict(text=t["batch_hist_title"], font=dict(size=13,color="#1a2e44"), x=0),
            xaxis=dict(title=t["batch_hist_xy"][0], tickfont=dict(size=10), fixedrange=True),
            yaxis=dict(title=t["batch_hist_xy"][1], tickfont=dict(size=10), fixedrange=True),
            height=300, margin=dict(l=10,r=10,t=40,b=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="sans-serif"), dragmode=False,
        )
        st.plotly_chart(fig2, use_container_width=True, config=CHART_CONFIG)


# ============================================================
# YAN MENÜ
# ============================================================
lang = st.session_state.get("lang", "TR")
t    = T[lang]

# Dil
st.sidebar.markdown("""
<div style="text-align:center;padding:1.2rem 0 0.6rem 0;">
    <div class="logo-mark" style="margin:0 auto;">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 17L9 11L13 15L21 7" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M15 7H21V13" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
    <div style="font-weight:800;font-size:1.05rem;color:#005b96;margin-top:0.5rem;">Churn AI</div>
    <div style="font-size:0.73rem;color:#6c757d;margin-top:0.1rem;">{}</div>
</div>
<hr style="margin:0.4rem 0 0.8rem 0;border:none;border-top:2px solid #dce3eb;">
""".format(t["app_sub"]), unsafe_allow_html=True)

def _switch_lang(new_lang: str):
    st.session_state["lang"] = new_lang
    # Senaryo isimleri dile göre değiştiği için eski what-if tablosu tutarsız kalır
    st.session_state.pop("whatif_table", None)
    st.session_state.pop("balloons_shown", None)
    st.rerun()

lang_col1, lang_col2 = st.sidebar.columns(2)
if lang_col1.button("🇹🇷 Türkçe", use_container_width=True,
                    type="primary" if lang=="TR" else "secondary"):
    _switch_lang("TR")
if lang_col2.button("🇬🇧 English", use_container_width=True,
                    type="primary" if lang=="EN" else "secondary"):
    _switch_lang("EN")

st.sidebar.divider()

# Backend sağlık
is_alive       = check_api_health()
dot, hlbl      = ("🟢", t["backend_ok"]) if is_alive else ("🔴", t["backend_fail"])
hbg, hclr      = ("#e6f4ea","#1a6e35") if is_alive else ("#fdecea","#a31515")
st.sidebar.markdown(f"""
<div style="background:{hbg};border-radius:8px;padding:0.5rem 0.85rem;
            font-size:0.82rem;color:{hclr};font-weight:600;margin-bottom:0.8rem;">
    {dot} {hlbl}
</div>""", unsafe_allow_html=True)

# Müşteri formu
st.sidebar.header(t["sidebar_header"])
user_data = get_user_input(t)

col_run, col_reset = st.sidebar.columns(2)
if col_run.button(t["analyze_btn"], use_container_width=True, type="primary"):
    with st.spinner("..."):
        result, err = call_predict_api(user_data)
    if err:
        st.sidebar.error(f"⚠️ {err}")
    else:
        st.session_state["current_data"]   = user_data
        st.session_state["result"]         = result
        st.session_state.pop("whatif_table", None)
        st.session_state["balloons_shown"] = False

if col_reset.button(t["clear_btn"], use_container_width=True):
    for k in ["result","current_data","whatif_table","batch_result","balloons_shown","last_csv_id"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.divider()


# ============================================================
# ANA İÇERİK
# ============================================================
st.markdown(f"""
<div class="hero-header">
    <div class="hero-badge">{t['hero_badge']}</div>
    <div class="hero-title-row">
        <div class="logo-mark logo-mark-ghost">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 17L9 11L13 15L21 7" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M15 7H21V13" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <h1 style="margin:0;">{t['hero_title']}</h1>
    </div>
    <p style="margin-top:0.6rem;">{t['hero_sub']}</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs([t["tab1"], t["tab2"]], key="main_tabs")


# ── TAB 1: TEKİL ──────────────────────────────────────────
with tab1:
    if "result" in st.session_state:
        res      = st.session_state["result"]
        prob     = res.get("churn_probability", 0)
        is_risky = res.get("churn_prediction") == 1
        data     = st.session_state["current_data"]

        level_name, level_color, level_icon = get_risk_level(prob, t)
        sub_text = t["risky_sub"] if is_risky else t["safe_sub"]

        st.markdown(f"""
        <div style="border-radius:14px;padding:1.4rem 2rem;margin-bottom:1rem;
                    box-shadow:0 4px 20px rgba(0,0,0,0.07);
                    background:linear-gradient(135deg,{level_color}08 0%,{level_color}15 100%);
                    border:2px solid {level_color};">
            <p style="font-size:0.75rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.8px;color:#6c757d;margin:0 0 0.3rem 0;">{t['result_label']}</p>
            <p style="font-size:1.5rem;font-weight:800;margin:0 0 0.3rem 0;color:{level_color};">
                {level_icon} {level_name}
            </p>
            <p style="font-size:0.87rem;color:#6c757d;margin:0;">{sub_text}</p>
        </div>
        """, unsafe_allow_html=True)

        gcol1, gcol2 = st.columns([1.1, 0.9])
        with gcol1:
            render_gauge(prob, level_color, t)
        with gcol2:
            render_customer_profile_card(data, prob, t)

        st.divider()
        render_shap_chart(data, t)

        if is_risky:
            st.divider()
            st.markdown(f'<p class="section-title">{t["whatif_title"]}</p>', unsafe_allow_html=True)
            st.info(t["whatif_info"], icon="💡")
            render_whatif_table(data, prob, t)
    else:
        st.markdown(f"""
        <div class="cta-panel">
            <div style="font-size:2.8rem;margin-bottom:0.6rem;">👈</div>
            <div style="font-size:1.05rem;font-weight:700;color:#1a2e44;margin-bottom:0.35rem;">{t['cta_title']}</div>
            <div style="font-size:0.88rem;color:#6c757d;">{t['cta_sub']}</div>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 2: TOPLU ──────────────────────────────────────────
with tab2:
    uploaded_file = st.file_uploader(t["batch_upload"], type=["csv"], key="csv_uploader")

    if uploaded_file is not None:
        # Farklı bir dosya yüklendiyse önceki analizin kalıntı sonuçlarını temizle
        current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_csv_id") != current_file_id:
            st.session_state.pop("batch_result", None)
            st.session_state["last_csv_id"] = current_file_id

        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"CSV okunamadı: {e}"); st.stop()

        st.markdown(f'<p class="section-title">{t["batch_preview"]}</p>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=240)
        st.info(t["batch_found"](len(df)), icon="ℹ️")

        max_workers = st.slider(t["batch_workers"], 1, 10, 5)

        if st.button(t["batch_start"], type="primary", use_container_width=True):
            payloads = [build_payload_from_row(row) for _, row in df.iterrows()]
            results  = [None] * len(payloads)
            errors   = [None] * len(payloads)
            bar = st.progress(0.0, text="..."); done = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                fti = {executor.submit(call_predict_api, p): i for i, p in enumerate(payloads)}
                for future in as_completed(fti):
                    idx = fti[future]
                    results[idx], errors[idx] = future.result()
                    done += 1
                    bar.progress(done/len(payloads), text=t["batch_progress"](done, len(payloads)))
            bar.empty()

            probs, preds, statuses = [], [], []
            for res, err in zip(results, errors):
                if res:
                    probs.append(res.get("churn_probability"))
                    preds.append(res.get("churn_prediction"))
                    statuses.append(res.get("risk_status"))
                else:
                    probs.append(None); preds.append(None); statuses.append(f"Hata: {err}")

            df_result = df.copy()
            df_result["Terk Olasılığı (%)"] = probs
            df_result["Risk Durumu"]        = statuses
            df_result["Tahmin"]             = preds
            st.session_state["batch_result"] = df_result

        if "batch_result" in st.session_state:
            df_result     = st.session_state["batch_result"]
            valid         = df_result[df_result["Tahmin"].notna()]
            failed        = len(df_result) - len(valid)
            high_risk_cnt = int((valid["Tahmin"]==1).sum()) if len(valid) else 0
            low_risk_cnt  = len(valid) - high_risk_cnt
            avg_prob      = valid["Terk Olasılığı (%)"].mean() if len(valid) else 0

            st.divider()
            st.markdown(f'<p class="section-title">{t["batch_results"]}</p>', unsafe_allow_html=True)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric(t["batch_metrics"][0], len(df_result))
            c2.metric(t["batch_metrics"][1], high_risk_cnt,
                      delta=f"%{high_risk_cnt/max(len(df_result),1)*100:.1f}", delta_color="inverse")
            c3.metric(t["batch_metrics"][2], low_risk_cnt,
                      delta=f"%{low_risk_cnt/max(len(df_result),1)*100:.1f}")
            c4.metric(t["batch_metrics"][3], f"%{avg_prob:.2f}" if len(valid) else "N/A")

            if failed > 0: st.warning(t["batch_failed"](failed))

            st.markdown(f'<p class="section-title">{t["batch_viz"]}</p>', unsafe_allow_html=True)
            render_batch_charts(valid, high_risk_cnt, low_risk_cnt, t)

            bt1, bt2 = st.tabs(t["batch_tabs"])
            with bt1: st.dataframe(df_result, use_container_width=True)
            with bt2:
                hr_df = valid[valid["Tahmin"]==1]
                st.dataframe(hr_df, use_container_width=True) if len(hr_df) else st.success(t["batch_no_risky"])

            csv_bytes = df_result.to_csv(index=False).encode("utf-8-sig")
            st.download_button(t["batch_download"], data=csv_bytes,
                               file_name="churn_analiz_sonuclari.csv",
                               mime="text/csv", use_container_width=True)
    else:
        st.session_state.pop("batch_result", None)
        st.session_state.pop("last_csv_id", None)
        st.markdown(f"""
        <div class="empty-drop">
            <div class="empty-drop-icon">📂</div>
            <div class="empty-drop-title">{t['batch_empty_title']}</div>
            <div class="empty-drop-sub">{t['batch_empty_sub']}</div>
        </div>
        """, unsafe_allow_html=True)