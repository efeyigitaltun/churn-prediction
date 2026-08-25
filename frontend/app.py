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
REQUEST_TIMEOUT = 10

st.set_page_config(
    page_title="Churn Karar Destek Sistemi",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

if "api_url" not in st.session_state:
    st.session_state["api_url"] = DEFAULT_API_URL

# ============================================================
# ÖZEL CSS
# ============================================================
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    .hero-header {
        background: linear-gradient(135deg, #003f6b 0%, #005b96 55%, #0077c2 100%);
        border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem;
        color: white; box-shadow: 0 6px 28px rgba(0,91,150,0.28);
    }
    .hero-header h1 {
        font-size: 1.85rem; font-weight: 800; margin: 0 0 0.45rem 0;
        letter-spacing: -0.4px; color: white !important;
    }
    .hero-header p { font-size: 0.97rem; opacity: 0.88; margin: 0; }
    .hero-badge {
        display: inline-block; background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.3); border-radius: 50px;
        padding: 0.2rem 0.85rem; font-size: 0.75rem; margin-bottom: 0.75rem;
        letter-spacing: 0.6px; text-transform: uppercase; font-weight: 600;
    }

    .section-title {
        font-size: 1.05rem; font-weight: 700; color: #1a2e44;
        margin: 0 0 1rem 0; padding-bottom: 0.4rem;
        border-bottom: 2px solid #005b96; display: inline-block;
    }

    .summary-chip {
        display: inline-block; background: #f0f4f8;
        border: 1px solid #dce3eb; border-radius: 8px;
        padding: 0.35rem 0.75rem; font-size: 0.82rem;
        margin: 0.2rem 0.15rem; color: #374151;
    }
    .summary-chip b { color: #005b96; }

    .cta-panel {
        text-align: center; background: #f0f6ff; border-radius: 14px;
        padding: 2.5rem 2rem; border: 2px dashed #aac8e8; margin-top: 1rem;
    }
    .empty-drop {
        text-align: center; background: #f0f6ff; border-radius: 14px;
        padding: 3rem 2rem; border: 2px dashed #aac8e8; margin-top: 1rem;
    }
    .empty-drop-icon  { font-size: 3rem; margin-bottom: 0.6rem; }
    .empty-drop-title { font-size: 1.05rem; font-weight: 700; color: #1a2e44; margin-bottom: 0.35rem; }
    .empty-drop-sub   { font-size: 0.88rem; color: #6c757d; }

    [data-testid="metric-container"] {
        background: white; border-radius: 12px; padding: 1rem 1.2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06); border: 1px solid #e9ecef;
    }

    div[data-testid="stButton"] > button {
        border-radius: 10px; font-weight: 600; transition: all 0.2s ease;
    }
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-2px); box-shadow: 0 5px 14px rgba(0,0,0,0.14);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f0f4f8; border-right: 2px solid #dce3eb;
    }

    /* Sadece label font stili — kart sarmalayıcı YOK */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label {
        font-size: 0.82rem;
        font-weight: 700;
        color: #374151;
    }

    /* Selectbox her zaman çerçeveli */
    div[data-baseweb="select"] > div:first-child {
        border: 1.5px solid #ced4da !important; border-radius: 8px !important;
        background-color: white !important; transition: border-color 0.2s, box-shadow 0.2s;
    }
    div[data-baseweb="select"] > div:first-child:hover { border-color: #005b96 !important; }
    div[data-baseweb="select"] > div:first-child:focus-within {
        border-color: #005b96 !important;
        box-shadow: 0 0 0 3px rgba(0,91,150,0.15) !important;
    }

    input[type="number"], input[type="text"] {
        border: 1.5px solid #ced4da !important; border-radius: 8px !important;
    }
    input[type="number"]:focus, input[type="text"]:focus {
        border-color: #005b96 !important;
        box-shadow: 0 0 0 3px rgba(0,91,150,0.15) !important;
        outline: none !important;
    }

    .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background: #f0f4f8; border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 600; padding: 0.45rem 1.2rem; }
    div[data-testid="stAlert"] { border-radius: 10px; }
    .stProgress > div > div > div { border-radius: 50px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================
def get_risk_level(prob: float) -> tuple:
    if prob < 30:   return "Düşük Risk",  "#198754", "🟢"
    elif prob < 60: return "Orta Risk",   "#fd7e14", "🟡"
    elif prob < 80: return "Yüksek Risk", "#e67e22", "🟠"
    else:           return "Kritik Risk", "#dc3545", "🔴"


def estimate_feature_contributions(data: dict) -> dict:
    c = {}
    c["Sözleşme Türü"] = {
        "Month-to-month": 28, "One year": -12, "Two year": -22
    }.get(data.get("Contract"), 0)

    tenure = int(data.get("tenure", 0))
    if   tenure <= 3:  c["Müşterilik Süresi"] = 24
    elif tenure <= 12: c["Müşterilik Süresi"] = 14
    elif tenure <= 36: c["Müşterilik Süresi"] = 2
    else:              c["Müşterilik Süresi"] = -20

    c["İnternet Servisi"] = {
        "Fiber optic": 15, "DSL": -5, "No": -12
    }.get(data.get("InternetService"), 0)

    mc = float(data.get("MonthlyCharges", 0))
    if   mc > 90: c["Aylık Fatura"] = 20
    elif mc > 70: c["Aylık Fatura"] = 12
    elif mc > 50: c["Aylık Fatura"] = 4
    else:         c["Aylık Fatura"] = -6

    c["Çevrimiçi Güvenlik"] = {
        "No": 10, "Yes": -8, "No internet service": -12
    }.get(data.get("OnlineSecurity"), 0)

    c["Teknik Destek"] = {
        "No": 9, "Yes": -7, "No internet service": -10
    }.get(data.get("TechSupport"), 0)

    if data.get("PaymentMethod") == "Electronic check":
        c["Ödeme Yöntemi"] = 11
    elif data.get("PaymentMethod") in ["Bank transfer (automatic)", "Credit card (automatic)"]:
        c["Ödeme Yöntemi"] = -5
    else:
        c["Ödeme Yöntemi"] = 0

    c["Kağıtsız Fatura"] = {"Yes": 5, "No": -3}.get(data.get("PaperlessBilling"), 0)
    c["Yaş Grubu"]       = 7 if data.get("SeniorCitizen") == 1 else -3

    has_partner = data.get("Partner") == "Yes"
    has_dep     = data.get("Dependents") == "Yes"
    if not has_partner and not has_dep: c["Aile/Sosyal Bağ"] = 8
    elif has_partner or has_dep:        c["Aile/Sosyal Bağ"] = -5
    else:                               c["Aile/Sosyal Bağ"] = -9

    return c


def check_api_health() -> bool:
    base_url = st.session_state.get("api_url", DEFAULT_API_URL).replace("/predict", "/")
    try:
        r = requests.get(base_url, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def call_predict_api(payload: dict, timeout: int = REQUEST_TIMEOUT):
    url = st.session_state.get("api_url", DEFAULT_API_URL)
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, "API'ye bağlanılamadı. Backend sunucusunun (uvicorn) çalıştığından emin olun."
    except requests.exceptions.Timeout:
        return None, "İstek zaman aşımına uğradı."
    except requests.exceptions.HTTPError:
        return None, f"API hatası (HTTP {response.status_code}): {response.text[:200]}"
    except Exception as e:
        return None, f"Beklenmeyen hata: {e}"


def to_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_payload_from_row(row: pd.Series) -> dict:
    def g(col, default=None):
        return row[col] if col in row and pd.notna(row[col]) else default

    senior_raw = g("SeniorCitizen", 0)
    try:
        senior = int(to_float(senior_raw))
    except (ValueError, TypeError):
        senior = 1 if str(senior_raw).strip().lower() in ("evet", "yes", "1", "true") else 0

    return {
        "gender": g("gender", "Female"), "SeniorCitizen": senior,
        "Partner": g("Partner", "No"), "Dependents": g("Dependents", "No"),
        "tenure": int(to_float(g("tenure", 0))), "PhoneService": g("PhoneService", "Yes"),
        "MultipleLines": g("MultipleLines", "No"), "InternetService": g("InternetService", "DSL"),
        "OnlineSecurity": g("OnlineSecurity", "No"), "OnlineBackup": g("OnlineBackup", "No"),
        "DeviceProtection": g("DeviceProtection", "No"), "TechSupport": g("TechSupport", "No"),
        "StreamingTV": g("StreamingTV", "No"), "StreamingMovies": g("StreamingMovies", "No"),
        "Contract": g("Contract", "Month-to-month"), "PaperlessBilling": g("PaperlessBilling", "Yes"),
        "PaymentMethod": g("PaymentMethod", "Electronic check"),
        "MonthlyCharges": to_float(g("MonthlyCharges", 0.0)),
        "TotalCharges": to_float(g("TotalCharges", 0.0)),
    }


def get_user_input() -> dict:
    TR = {"Evet": "Yes", "Hayır": "No"}

    with st.sidebar.expander("👤 Demografik Bilgiler", expanded=True):
        gender     = st.selectbox("Cinsiyet", ["Female", "Male"])
        senior     = st.selectbox("Yaşlı Mı?", ["Hayır", "Evet"])
        partner_tr = st.selectbox("Partneri Var Mı?", ["Evet", "Hayır"])
        dep_tr     = st.selectbox("Bakmakla Yükümlü Olduğu Biri Var Mı?", ["Evet", "Hayır"])

    with st.sidebar.expander("🌐 Alınan Hizmetler", expanded=False):
        phone_tr = st.selectbox("Telefon Servisi", ["Evet", "Hayır"])
        if phone_tr == "Hayır":
            multiple_lines = "No phone service"
            st.caption("ℹ️ Telefon servisi olmadığından 'Çoklu Hat' otomatik devre dışı.")
        else:
            multi_tr       = st.selectbox("Çoklu Hat", ["Evet", "Hayır"])
            multiple_lines = TR[multi_tr]

        internet_opts    = {"DSL": "DSL", "Fiber Optik": "Fiber optic", "Yok": "No"}
        internet_tr      = st.selectbox("İnternet Servisi", list(internet_opts.keys()))
        internet_service = internet_opts[internet_tr]

        if internet_service == "No":
            online_security = online_backup = device_protection = "No internet service"
            tech_support = streaming_tv = streaming_movies      = "No internet service"
            st.caption("ℹ️ İnternet servisi olmadığından bağımlı hizmetler otomatik devre dışı.")
        else:
            os_tr  = st.selectbox("Çevrimiçi Güvenlik",  ["Evet", "Hayır"])
            ob_tr  = st.selectbox("Çevrimiçi Yedekleme", ["Evet", "Hayır"])
            dp_tr  = st.selectbox("Cihaz Koruması",       ["Evet", "Hayır"])
            ts_tr  = st.selectbox("Teknik Destek",         ["Evet", "Hayır"])
            stv_tr = st.selectbox("TV Yayını",             ["Evet", "Hayır"])
            sm_tr  = st.selectbox("Film Yayını",           ["Evet", "Hayır"])
            online_security   = TR[os_tr];  online_backup     = TR[ob_tr]
            device_protection = TR[dp_tr];  tech_support      = TR[ts_tr]
            streaming_tv      = TR[stv_tr]; streaming_movies  = TR[sm_tr]

    with st.sidebar.expander("💳 Sözleşme & Fatura", expanded=False):
        tenure   = st.number_input("Müşterilik Süresi (Ay)", min_value=0, max_value=100, value=1)
        contract = st.selectbox("Sözleşme Türü", ["Month-to-month", "One year", "Two year"])
        pb_tr    = st.selectbox("Kağıtsız Fatura", ["Evet", "Hayır"])
        payment_method = st.selectbox("Ödeme Yöntemi", [
            "Electronic check", "Mailed check",
            "Bank transfer (automatic)", "Credit card (automatic)",
        ])
        monthly_charges = st.number_input("Aylık Fatura ($)", min_value=0.0, value=70.70)
        total_charges   = st.number_input("Toplam Harcama ($)", min_value=0.0, value=70.70)
        st.caption(f"💡 Referans tahmini (Aylık × Süre): ${monthly_charges * tenure:,.2f}")

    return {
        "gender": gender, "SeniorCitizen": 1 if senior == "Evet" else 0,
        "Partner": TR[partner_tr], "Dependents": TR[dep_tr], "tenure": tenure,
        "PhoneService": TR[phone_tr], "MultipleLines": multiple_lines,
        "InternetService": internet_service, "OnlineSecurity": online_security,
        "OnlineBackup": online_backup, "DeviceProtection": device_protection,
        "TechSupport": tech_support, "StreamingTV": streaming_tv,
        "StreamingMovies": streaming_movies, "Contract": contract,
        "PaperlessBilling": TR[pb_tr], "PaymentMethod": payment_method,
        "MonthlyCharges": monthly_charges, "TotalCharges": total_charges,
    }


def render_gauge(prob: float, level_color: str):
    if not PLOTLY_AVAILABLE:
        return
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=prob,
        number={"suffix": "%", "font": {"size": 44, "color": level_color, "family": "sans-serif"}},
        delta={
            "reference": 50, "suffix": " puan (eşikten)",
            "font": {"size": 13},
            "increasing": {"color": "#dc3545"}, "decreasing": {"color": "#198754"},
        },
        title={"text": "Terk Olasılığı", "font": {"size": 13, "color": "#6c757d"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#adb5bd",
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
        height=270, margin=dict(l=25, r=25, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "sans-serif"},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_shap_chart(data: dict):
    if not PLOTLY_AVAILABLE:
        return
    contributions = estimate_feature_contributions(data)
    sorted_items  = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
    features = [i[0] for i in reversed(sorted_items)]
    values   = [i[1] for i in reversed(sorted_items)]
    colors   = ["#e53e3e" if v > 0 else "#2d8c4e" for v in values]
    text     = [f"+{v}" if v > 0 else str(v) for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=features, orientation="h",
        marker_color=colors, marker_line=dict(color="white", width=0),
        text=text, textposition="outside", textfont=dict(size=11), cliponaxis=False,
    ))
    fig.add_vline(x=0, line_color="#6c757d", line_width=1.5)
    x_max = max(abs(v) for v in values) if values else 1
    fig.add_annotation(x=x_max * 0.55, y=-1.3, xref="x", yref="y",
                       text="🔴 Riski Artırıyor", showarrow=False,
                       font=dict(size=10, color="#e53e3e"))
    fig.add_annotation(x=-x_max * 0.55, y=-1.3, xref="x", yref="y",
                       text="🟢 Riski Azaltıyor", showarrow=False,
                       font=dict(size=10, color="#2d8c4e"))
    fig.update_layout(
        title=dict(text="📊 Risk Faktörleri Analizi",
                   font=dict(size=13, color="#1a2e44"), x=0),
        xaxis=dict(title="Katkı Puanı", showgrid=True,
                   gridcolor="#f0f4f8", zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11)),
        height=340, margin=dict(l=10, r=70, t=45, b=45),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, font=dict(family="sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_customer_profile_card(data: dict, prob: float):
    level_name, level_color, level_icon = get_risk_level(prob)
    internet_tr = {"DSL": "DSL", "Fiber optic": "Fiber Optik", "No": "Yok"}.get(
        data.get("InternetService", ""), data.get("InternetService", ""))
    st.markdown(f"""
    <div style="background:white; border-radius:12px; padding:1.2rem 1.4rem;
                border:1px solid #e9ecef; box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase;
                    letter-spacing:0.8px; color:#6c757d; margin-bottom:0.8rem;">👤 Müşteri Profili</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.6rem 1rem; font-size:0.84rem;">
            <div><div style="color:#6c757d;font-size:0.72rem;">Cinsiyet</div>
                 <b>{data.get('gender','—')}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Yaş Grubu</div>
                 <b>{'Yaşlı (65+)' if data.get('SeniorCitizen') else 'Standart'}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Müşterilik</div>
                 <b>{data.get('tenure',0)} ay</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Sözleşme</div>
                 <b>{data.get('Contract','—')}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">İnternet</div>
                 <b>{internet_tr}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Aylık Fatura</div>
                 <b>${data.get('MonthlyCharges',0):.2f}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Ödeme</div>
                 <b style="font-size:0.76rem;">{data.get('PaymentMethod','—')}</b></div>
            <div><div style="color:#6c757d;font-size:0.72rem;">Partner</div>
                 <b>{'Var' if data.get('Partner')=='Yes' else 'Yok'}</b></div>
        </div>
        <div style="margin-top:0.9rem; padding-top:0.7rem; border-top:1px solid #f0f0f0;">
            <span style="background:{level_color}18; color:{level_color};
                         border:1.5px solid {level_color}; border-radius:50px;
                         padding:0.25rem 0.9rem; font-size:0.8rem; font-weight:700;">
                {level_icon} {level_name}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_whatif_table(base_data: dict, base_prob: float):
    SCENARIOS = {
        "📊 Mevcut Durum":        None,
        "🎁 1 Yıllık Taahhüt":   {"Contract": "One year"},
        "🎁 2 Yıllık Taahhüt":   {"Contract": "Two year"},
        "💸 %15 Fatura İndirimi": {"MonthlyCharges": base_data.get("MonthlyCharges", 0) * 0.85},
        "🚀 Fiber Optik":          {"InternetService": "Fiber optic"},
    }

    if st.button("🔄 Tüm Senaryoları Karşılaştır", type="primary",
                 use_container_width=True, key="whatif_all"):
        scenario_probs = {"📊 Mevcut Durum": base_prob}
        with st.spinner("4 senaryo paralel simüle ediliyor..."):
            payloads = {}
            for name, mod in SCENARIOS.items():
                if mod is None:
                    continue
                payloads[name] = {**base_data, **mod}
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(call_predict_api, d): n
                           for n, d in payloads.items()}
                for future in as_completed(futures):
                    name = futures[future]
                    res, _ = future.result()
                    scenario_probs[name] = res["churn_probability"] if res else None

        rows = []
        for name in SCENARIOS:
            prob = scenario_probs.get(name)
            if prob is None:
                continue
            diff = round(prob - base_prob, 1)
            level_name, _, level_icon = get_risk_level(prob)
            rows.append({
                "Senaryo":       name,
                "Risk (%)":      round(prob, 1),
                "Değişim":       diff,
                "Risk Seviyesi": f"{level_icon} {level_name}",
            })
        st.session_state["whatif_table"]   = rows
        st.session_state["balloons_shown"] = False

    if "whatif_table" in st.session_state:
        rows     = st.session_state["whatif_table"]
        df       = pd.DataFrame(rows)
        non_base = df[df["Senaryo"] != "📊 Mevcut Durum"]

        if len(non_base):
            best     = non_base.loc[non_base["Risk (%)"].idxmin()]
            diff_pct = base_prob - best["Risk (%)"]
            if diff_pct >= base_prob * 0.3 and not st.session_state.get("balloons_shown", False):
                st.success(
                    f"🎉 En iyi senaryo: **{best['Senaryo']}** — "
                    f"Risk **%{base_prob:.1f}'den %{best['Risk (%)']:.1f}'e düşüyor!** "
                    f"({diff_pct:.1f} puan iyileşme)"
                )
                st.balloons()
                st.session_state["balloons_shown"] = True
            elif diff_pct > 0:
                st.info(f"💡 En iyi senaryo: **{best['Senaryo']}** — "
                        f"Risk %{base_prob:.1f}'den %{best['Risk (%)']:.1f}'e düşüyor.")

        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "Risk (%)": st.column_config.ProgressColumn(
                    "Risk (%)", min_value=0, max_value=100, format="%.1f%%"),
                "Değişim": st.column_config.NumberColumn("Değişim (puan)", format="%.1f"),
            }
        )


def render_batch_charts(valid_df: pd.DataFrame, high_risk_cnt: int, low_risk_cnt: int):
    if not PLOTLY_AVAILABLE:
        return
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(data=[go.Pie(
            labels=["🚨 Yüksek Riskli", "✅ Sadık Müşteri"],
            values=[high_risk_cnt, low_risk_cnt], hole=0.65,
            marker=dict(colors=["#dc3545", "#198754"], line=dict(color="white", width=2)),
            textinfo="label+percent", textfont=dict(size=11),
            hovertemplate="%{label}: %{value} müşteri (%{percent})<extra></extra>",
        )])
        fig.update_layout(
            title=dict(text="Müşteri Risk Dağılımı", font=dict(size=13, color="#1a2e44"), x=0.5),
            height=300, margin=dict(l=10, r=10, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<b>{high_risk_cnt + low_risk_cnt}</b><br>Müşteri",
                x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#1a2e44"),
            )],
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        probs = valid_df["Terk Olasılığı (%)"].dropna().tolist()
        fig2  = go.Figure(go.Histogram(
            x=probs, nbinsx=20, marker_color="#005b96",
            marker_line=dict(color="white", width=0.5),
            hovertemplate="Risk: %{x:.1f}%<br>Müşteri: %{y}<extra></extra>",
        ))
        fig2.add_vline(x=50, line_color="#dc3545", line_width=2, line_dash="dash",
                       annotation_text="Eşik (50%)", annotation_position="top right",
                       annotation_font=dict(size=10, color="#dc3545"))
        fig2.update_layout(
            title=dict(text="Risk Skoru Dağılımı", font=dict(size=13, color="#1a2e44"), x=0),
            xaxis=dict(title="Terk Olasılığı (%)", tickfont=dict(size=10)),
            yaxis=dict(title="Müşteri Sayısı", tickfont=dict(size=10)),
            height=300, margin=dict(l=10, r=10, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="sans-serif"),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# YAN MENÜ
# ============================================================
st.sidebar.markdown("""
<div style="text-align:center; padding:1.2rem 0 0.6rem 0;">
    <div style="font-size:2.2rem; line-height:1;">📊</div>
    <div style="font-weight:800; font-size:1.05rem; color:#005b96; margin-top:0.3rem;">Churn AI</div>
    <div style="font-size:0.73rem; color:#6c757d; margin-top:0.1rem;">Karar Destek Sistemi</div>
</div>
<hr style="margin:0.4rem 0 0.8rem 0; border:none; border-top:2px solid #dce3eb;">
""", unsafe_allow_html=True)

is_alive = check_api_health()
dot, hlbl = ("🟢", "Backend Bağlı") if is_alive else ("🔴", "Backend Bağlantı Yok")
hbg, hclr = ("#e6f4ea", "#1a6e35") if is_alive else ("#fdecea", "#a31515")
st.sidebar.markdown(f"""
<div style="background:{hbg}; border-radius:8px; padding:0.5rem 0.85rem;
            font-size:0.82rem; color:{hclr}; font-weight:600; margin-bottom:0.8rem;">
    {dot} {hlbl}
</div>
""", unsafe_allow_html=True)

st.sidebar.header("📋 Müşteri Bilgileri")
user_data = get_user_input()

col_run, col_reset = st.sidebar.columns(2)
if col_run.button("🔍 Analiz Yap", use_container_width=True, type="primary"):
    with st.spinner("Model çalıştırılıyor..."):
        result, err = call_predict_api(user_data)
    if err:
        st.sidebar.error(f"⚠️ {err}")
    else:
        st.session_state["current_data"]   = user_data
        st.session_state["result"]         = result
        st.session_state.pop("whatif_table", None)
        st.session_state["balloons_shown"] = False

if col_reset.button("🔄 Temizle", use_container_width=True):
    for key in ["result", "current_data", "whatif_table", "batch_result", "balloons_shown"]:
        st.session_state.pop(key, None)
    st.rerun()

with st.sidebar.expander("⚙️ Gelişmiş Ayarlar", expanded=False):
    st.session_state["api_url"] = st.text_input("API Adresi", value=st.session_state["api_url"])

st.sidebar.divider()


# ============================================================
# ANA İÇERİK
# ============================================================
st.markdown("""
<div class="hero-header">
    <div class="hero-badge">🤖 AI Destekli · Gerçek Zamanlı</div>
    <h1>📊 Müşteri Terk (Churn) Karar Destek Sistemi</h1>
    <p>Tekil müşteri risk analizi ve toplu CSV analizi için entegre karar destek platformu.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["👤 Tekil Müşteri Analizi", "📁 Toplu Müşteri Analizi (CSV)"])


# ── TAB 1: TEKİL ──────────────────────────────────────────
with tab1:
    if "result" in st.session_state:
        res      = st.session_state["result"]
        prob     = res.get("churn_probability", 0)
        status   = res.get("risk_status", "")
        is_risky = res.get("churn_prediction") == 1
        data     = st.session_state["current_data"]

        level_name, level_color, level_icon = get_risk_level(prob)
        sub_text = ("Bu müşteri için acil aksiyon önerilir. Aşağıdan simülatörü kullanın."
                    if is_risky else "Müşteri sadık görünüyor. Mevcut hizmet kalitesini koruyun.")

        st.markdown(f"""
        <div style="border-radius:14px; padding:1.4rem 2rem; margin-bottom:1rem;
                    box-shadow:0 4px 20px rgba(0,0,0,0.07);
                    background:linear-gradient(135deg,{level_color}08 0%,{level_color}15 100%);
                    border:2px solid {level_color};">
            <p style="font-size:0.75rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.8px;color:#6c757d;margin:0 0 0.3rem 0;">Risk Analiz Sonucu</p>
            <p style="font-size:1.5rem;font-weight:800;margin:0 0 0.3rem 0;color:{level_color};">
                {level_icon} {level_name} — {status}
            </p>
            <p style="font-size:0.87rem;color:#6c757d;margin:0;">{sub_text}</p>
        </div>
        """, unsafe_allow_html=True)

        gcol1, gcol2 = st.columns([1.1, 0.9])
        with gcol1:
            render_gauge(prob, level_color)
        with gcol2:
            render_customer_profile_card(data, prob)

        st.divider()
        render_shap_chart(data)

        if is_risky:
            st.divider()
            st.markdown('<p class="section-title">💡 What-If Simülatörü — Müşteriyi Elde Tutma</p>',
                        unsafe_allow_html=True)
            st.info("Butona basın — 4 senaryo aynı anda API'ye gönderilir ve sonuçlar karşılaştırmalı tabloda gösterilir.", icon="💡")
            render_whatif_table(data, prob)

    else:
        st.markdown("""
        <div class="cta-panel">
            <div style="font-size:2.8rem;margin-bottom:0.6rem;">👈</div>
            <div style="font-size:1.05rem;font-weight:700;color:#1a2e44;margin-bottom:0.35rem;">
                Analiz için müşteri bilgilerini girin
            </div>
            <div style="font-size:0.88rem;color:#6c757d;">
                Sol menüden parametreleri belirleyip <strong>Analiz Yap</strong> butonuna tıklayın.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 2: TOPLU ──────────────────────────────────────────
with tab2:
    uploaded_file = st.file_uploader(
        "CSV formatında müşteri listesi yükleyin:", type=["csv"],
        help="Beklenen sütunlar: gender, SeniorCitizen, Partner, tenure, Contract, MonthlyCharges ...",
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"CSV okunamadı: {e}")
            st.stop()

        st.markdown('<p class="section-title">📋 Yüklenen Veri Önizleme</p>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=240)
        st.info(f"Tabloda toplam **{len(df)}** müşteri kaydı bulundu.", icon="ℹ️")

        max_workers = st.slider("⚡ Paralel istek sayısı", 1, 10, 5)

        if st.button("🚀 Tüm Liste İçin Risk Analizi Başlat", type="primary", use_container_width=True):
            payloads = [build_payload_from_row(row) for _, row in df.iterrows()]
            results  = [None] * len(payloads)
            errors   = [None] * len(payloads)
            bar  = st.progress(0.0, text="Analiz başlatılıyor...")
            done = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {executor.submit(call_predict_api, p): i
                                 for i, p in enumerate(payloads)}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    results[idx], errors[idx] = future.result()
                    done += 1
                    bar.progress(done / len(payloads),
                                 text=f"{done}/{len(payloads)} müşteri analiz edildi...")
            bar.empty()

            probs, preds, statuses = [], [], []
            for res, err in zip(results, errors):
                if res:
                    probs.append(res.get("churn_probability"))
                    preds.append(res.get("churn_prediction"))
                    statuses.append(res.get("risk_status"))
                else:
                    probs.append(None); preds.append(None)
                    statuses.append(f"Hata: {err}")

            df_result = df.copy()
            df_result["Terk Olasılığı (%)"] = probs
            df_result["Risk Durumu"]        = statuses
            df_result["Tahmin"]             = preds
            st.session_state["batch_result"] = df_result

        if "batch_result" in st.session_state:
            df_result     = st.session_state["batch_result"]
            valid         = df_result[df_result["Tahmin"].notna()]
            failed        = len(df_result) - len(valid)
            high_risk_cnt = int((valid["Tahmin"] == 1).sum()) if len(valid) else 0
            low_risk_cnt  = len(valid) - high_risk_cnt
            avg_prob      = valid["Terk Olasılığı (%)"].mean() if len(valid) else 0

            st.divider()
            st.markdown('<p class="section-title">📊 Analiz Sonuçları</p>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👥 Toplam Müşteri", len(df_result))
            c2.metric("🚨 Yüksek Riskli", high_risk_cnt,
                      delta=f"%{high_risk_cnt / max(len(df_result),1)*100:.1f}", delta_color="inverse")
            c3.metric("✅ Sadık Müşteri", low_risk_cnt,
                      delta=f"%{low_risk_cnt / max(len(df_result),1)*100:.1f}")
            c4.metric("📈 Ort. Terk Olasılığı", f"%{avg_prob:.2f}" if len(valid) else "N/A")

            if failed > 0:
                st.warning(f"⚠️ {failed} müşteri için analiz başarısız. Detaylar 'Risk Durumu' sütununda.")

            st.markdown('<p class="section-title">📈 Risk Görselleştirme</p>', unsafe_allow_html=True)
            render_batch_charts(valid, high_risk_cnt, low_risk_cnt)

            t1, t2 = st.tabs(["📋 Tüm Sonuçlar", "🚨 Yalnızca Yüksek Riskliler"])
            with t1:
                st.dataframe(df_result, use_container_width=True)
            with t2:
                hr_df = valid[valid["Tahmin"] == 1]
                if len(hr_df):
                    st.dataframe(hr_df, use_container_width=True)
                else:
                    st.success("🎉 Yüksek riskli müşteri bulunamadı!")

            csv_bytes = df_result.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Sonuçları CSV Olarak İndir", data=csv_bytes,
                               file_name="churn_analiz_sonuclari.csv",
                               mime="text/csv", use_container_width=True)
    else:
        st.markdown("""
        <div class="empty-drop">
            <div class="empty-drop-icon">📂</div>
            <div class="empty-drop-title">CSV Dosyası Bekleniyor</div>
            <div class="empty-drop-sub">Yukarıdaki alandan bir CSV dosyası yükleyerek toplu analiz başlatabilirsiniz.</div>
        </div>
        """, unsafe_allow_html=True)
