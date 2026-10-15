"""
app.py — EASY PASS Executive Dashboard (ฉบับสมบูรณ์)
การทางพิเศษแห่งประเทศไทย (กทพ.)

การแก้ไขล่าสุด:
- รวมแท็บ 🚗 ธุรกรรมสายทาง กทพ. + 🛣️ มอเตอร์เวย์/โทลล์เวย์ เป็นแท็บเดียว
  ชื่อ "🚗 ธุรกรรม Easy Pass/M-Pass"
- ปรับชื่อแท็บทั้งหมดให้สื่อความหมายชัดเจน
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import datetime
import base64

from auth import require_login, logout, ROLE_LABELS, get_audit_log
from settings_store import load_settings, update_thresholds, reset_thresholds_to_default, append_audit
from pdf_report import generate_pdf_report

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="EASY PASS Executive Dashboard | กทพ.",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "exat_logo.png"


def _img_to_base64(path):
    try:
        if not Path(path).exists():
            return None
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


LOGO_B64 = _img_to_base64(LOGO_PATH)


def get_user_display(user_dict, role_label):
    return f"{user_dict.get('username', '')} · {role_label}"


# ----------------------------------------------------------------------------
# CUSTOM CSS
# ----------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
    visibility: visible !important;
}
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    z-index: 999999 !important;
}
.main-header{position:relative; border-radius:14px; color:white; margin-bottom:18px; overflow:hidden;
    background: linear-gradient(135deg, #001233 0%, #003366 60%, #0B5ED7 100%);
    box-shadow: 0 6px 24px rgba(0,51,102,0.25);}
.main-header .content{position:relative; padding:22px 28px; display:flex;
    align-items:center; justify-content:space-between; gap:24px;}
.main-header h1{margin:0; font-size:28px; color:#FFFFFF !important;
    text-shadow: 0 3px 12px rgba(0,0,0,0.6), 0 0 30px rgba(11,94,215,0.4);
    font-weight:800; letter-spacing:0.4px;}
.main-header p{margin:6px 0 0 0; color:#E3F2FD !important; font-size:14px; font-weight:500;
    text-shadow: 0 1px 4px rgba(0,0,0,0.5);}
.main-header .header-meta{margin-top:12px; padding:8px 14px; background:rgba(255,255,255,0.18);
    border-radius:8px; display:inline-block; border:1px solid rgba(255,255,255,0.3);
    backdrop-filter:blur(4px);}
.main-header .header-meta span{color:#FFFFFF !important; font-size:13px; font-weight:500;}
.main-header .header-logo{height:110px; width:auto; flex-shrink:0; background:#FFFFFF;
    border-radius:12px; padding:8px 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.4);}

.alert-card{border-radius:10px; padding:14px 18px; margin-bottom:10px; color:white;}
.alert-critical{background:#D32F2F;} .alert-warning{background:#F57C00;} .alert-normal{background:#2E7D32;}
.user-badge{background:linear-gradient(135deg,#FFFFFF 0%,#F0F4FA 100%);
    border-radius:10px;padding:12px 14px;border-left:5px solid #0B5ED7;
    margin-bottom:10px;box-shadow:0 2px 6px rgba(0,51,102,0.08);}
.import-ok{background:#D4EDDA;border-radius:10px;padding:14px 18px;margin-bottom:10px;color:#155724;border-left:5px solid #2E7D32;}
.import-bad{background:#F8D7DA;border-radius:10px;padding:14px 18px;margin-bottom:10px;color:#721C24;border-left:5px solid #D32F2F;}
.section-title{background:#F0F4FA;padding:8px 14px;border-radius:8px;border-left:4px solid #0B5ED7;margin:14px 0 10px 0;font-weight:600;color:#003366;}
.sub-section-title{background:#FAFCFF;padding:6px 12px;border-radius:6px;border-left:3px solid #0288D1;margin:10px 0 8px 0;font-weight:600;color:#01579B;font-size:14px;}
.role-note{background:#FFF8E1;border-left:4px solid #F57C00;padding:10px 14px;border-radius:8px;margin-bottom:14px;font-size:13px;}
.kpi-tile{background:linear-gradient(135deg,#FFFFFF 0%,#F0F4FA 100%);
    border-radius:12px; padding:16px 18px; border-left:5px solid #0B5ED7;
    box-shadow:0 2px 8px rgba(0,51,102,0.08); margin-bottom:8px; height:100%;}
.kpi-tile.blue{border-left-color:#0B5ED7;} .kpi-tile.green{border-left-color:#2E7D32;}
.kpi-tile.orange{border-left-color:#F57C00;} .kpi-tile.red{border-left-color:#D32F2F;}
.kpi-tile.purple{border-left-color:#6A1B9A;} .kpi-tile.teal{border-left-color:#00838F;}
.kpi-tile.pink{border-left-color:#C2185B;} .kpi-tile.brown{border-left-color:#5D4037;}
.kpi-label{font-size:12.5px; color:#5A5A5A; font-weight:500; margin-bottom:6px;}
.kpi-value{font-size:24px; font-weight:700; color:#003366; line-height:1.1; margin-bottom:4px;}
.kpi-delta{font-size:12px; font-weight:600;}
.kpi-delta.up{color:#2E7D32;} .kpi-delta.down{color:#D32F2F;} .kpi-delta.flat{color:#757575;}
.exec-summary-box{background:linear-gradient(135deg,#F5F8FF 0%,#EBF2FC 100%);
    border-radius:12px;padding:18px 22px;border-left:5px solid #003366;margin-bottom:16px;}
.exec-summary-box h4{margin:0 0 10px 0;color:#003366;}
.exec-summary-box ul{margin:0;padding-left:22px;}
.exec-summary-box li{margin-bottom:6px;line-height:1.5;font-size:13.5px;color:#333;}
.quick-stat{background:#FFFFFF;border-radius:8px;padding:12px 14px;border:1px solid #E0E6ED; text-align:center; height:100%;}
.quick-stat .lbl{font-size:11.5px;color:#777;margin-bottom:4px;}
.quick-stat .val{font-size:17px;font-weight:700;color:#003366;}
.info-banner{background:linear-gradient(135deg,#E3F2FD 0%,#F0F8FF 100%);
    border-radius:10px; padding:12px 16px; border-left:4px solid #0288D1;
    margin-bottom:12px; font-size:13px; color:#0D47A1;}
.warning-banner{background:linear-gradient(135deg,#FFF3E0 0%,#FFF8E1 100%);
    border-radius:10px; padding:12px 16px; border-left:4px solid #F57C00;
    margin-bottom:12px; font-size:13px; color:#E65100;}
.success-banner{background:linear-gradient(135deg,#E8F5E9 0%,#F1F8E9 100%);
    border-radius:10px; padding:12px 16px; border-left:4px solid #2E7D32;
    margin-bottom:12px; font-size:13px; color:#1B5E20;}
.method-banner{background:linear-gradient(135deg,#F3E5F5 0%,#FCE4EC 100%);
    border-radius:10px; padding:12px 16px; border-left:4px solid #6A1B9A;
    margin-bottom:12px; font-size:13px; color:#4A148C;}
.zone-tile{background:#FFFFFF;border-radius:10px;padding:16px;border:1px solid #E0E6ED;
    border-left:5px solid #0B5ED7; margin-bottom:10px;}
.zone-tile.inner{border-left-color:#0288D1;}
.zone-tile.outer{border-left-color:#F57C00;}
.zone-tile .zt-title{font-size:13px;color:#555;font-weight:600;margin-bottom:8px;}
.zone-tile .zt-value{font-size:20px;font-weight:700;color:#003366;}
.zone-tile .zt-sub{font-size:11.5px;color:#777;margin-top:4px;}
.insight-card{background:#FFFFFF; border-radius:10px; padding:14px 18px;
    border-left:4px solid #0B5ED7; margin-bottom:10px; box-shadow:0 1px 4px rgba(0,0,0,0.05);}
.compare-tile{background:#FFFFFF; border-radius:12px; padding:18px 20px;
    border:1px solid #E0E6ED; text-align:center; box-shadow:0 2px 8px rgba(0,51,102,0.06);}
.compare-tile .ct-icon{font-size:32px; margin-bottom:6px;}
.compare-tile .ct-label{font-size:13px; color:#555; font-weight:600; margin-bottom:8px;}
.compare-tile .ct-value{font-size:22px; font-weight:700; color:#003366; margin-bottom:4px;}
.compare-tile .ct-sub{font-size:12px; color:#777;}
.pdf-page-tag{display:inline-block;background:#FFF3E0;color:#E65100;font-size:11px;
    font-weight:600;padding:3px 10px;border-radius:12px;margin-left:8px;vertical-align:middle;}
.scope-tag{display:inline-block;background:#E8F5E9;color:#1B5E20;font-size:11px;
    font-weight:600;padding:3px 10px;border-radius:12px;margin-left:8px;vertical-align:middle;}
.scope-tag.warn{background:#FFF3E0;color:#E65100;}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# LOGIN GATE
# ----------------------------------------------------------------------------
user = require_login()
role = user["role"]
is_admin = role == "admin"
is_governor = role == "governor"
is_executive = role == "executive"
is_viewer = role == "viewer"
can_export = role in ("admin", "governor", "executive")
show_operational_tabs = role in ("admin", "executive", "viewer")

app_settings = load_settings()
saved_th = app_settings.get("thresholds", {})

# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
if st.sidebar.button("🔄 รีเฟรชข้อมูลทั้งหมด", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(f"""
<div class="user-badge">
    <div style="font-size:14px; font-weight:700; color:#003366; margin-bottom:3px;">👤 {user['username']}</div>
    <div style="font-size:11.5px; color:#0B5ED7; font-weight:600;">{ROLE_LABELS[role]}</div>
</div>
""", unsafe_allow_html=True)
if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
    logout()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("🚗 EASY PASS Dashboard")
st.sidebar.caption("การทางพิเศษแห่งประเทศไทย (กทพ.)")
st.sidebar.markdown("---")

# ----------------------------------------------------------------------------
# DATASET REGISTRY
# ----------------------------------------------------------------------------
REQUIRED_COLUMNS = {
    "01_card_registration.csv": ["month", "month_label", "new_registrations", "cumulative_total"],
    "02_card_inventory.csv": ["month", "month_label", "obu_stock", "smartcard_stock"],
    "03_traffic_etc_overview.csv": ["month", "month_label", "total_traffic_million", "etc_traffic_million", "etc_percent", "avg_daily_etc"],
    "04_traffic_etc_by_route.csv": ["month", "month_label", "chalerm_mahanakorn", "srirat", "chalong_rat", "burapha_withi", "kanchanaphisek", "udornratthaya", "srirat_outer_ring"],
    "05_anomaly_events.csv": ["month", "month_label", "total_events", "cause_install", "cause_no_entry_data", "cause_low_balance", "cause_blacklist", "cause_equipment", "cause_other"],
    "06_emv_traffic.csv": ["month", "month_label", "total_traffic_million", "emv_traffic_million", "emv_percent"],
    "07_motorway_tollway.csv": ["month", "month_label", "motorway_transactions", "donmuang_tollway_transactions"],
    "08_topup_total.csv": ["month", "month_label", "total_baht", "external_agencies_baht", "internal_baht", "other_channel_baht"],
    "09_topup_edc.csv": ["month", "month_label", "cash_baht", "credit_baht", "debit_baht", "qr_baht"],
    "10_topup_external_agencies.csv": ["agency", "amount_baht", "share_percent"],
    "11_topup_digital_channel.csv": ["month", "month_label", "transactions", "amount_baht"],
    "12_website_stats.csv": ["month", "month_label", "new_registrations", "cumulative_total"],
    "13_card_status.csv": ["month", "month_label", "active_cards", "suspended_cards", "low_balance_cards", "lost_count", "lost_value_baht"],
    "14_customer_service.csv": ["month", "month_label", "total_cases"],
    "15_traffic_4wheel_etc.csv": ["month", "month_label", "total_traffic_million", "traffic_4wheel_million", "etc_total_million", "etc_4wheel_million", "etc_4wheel_percent"],
    "16_route_transactions_detail.csv": ["month", "month_label", "exat_total_transactions", "doh_m6_transactions", "doh_m7_transactions", "doh_m81_transactions"],
    "17_tollway_section_detail.csv": ["month", "month_label", "dindaeng_donmueang_transactions", "donmueang_anusorn_transactions", "total_tollway_transactions", "easypass_tollway_transactions", "easypass_percent"],
    "18_annual_cumulative_summary.csv": ["category", "metric_th", "value", "unit"],
    "19_card_registration_by_route.csv": ["route_code", "route_name", "monthly_aug69", "fy69_cumulative", "since_start"],
    "20_card_inventory_by_route.csv": ["route_name", "obu_stock", "smartcard_stock"],
    "21_traffic_etc_by_route_full.csv": ["route_code", "route_name", "zone", "total_traffic", "easypass_emv", "percent_easypass", "total_4wheel", "easypass_4wheel", "percent_4wheel", "emv_traffic", "emv_percent", "daily_total", "daily_etc"],
    "22_route_mpass_easypass.csv": ["route_code", "route_name", "group", "mpass_transactions", "mpass_percent", "easypass_transactions", "easypass_percent", "total_transactions", "avg_daily"],
    "23_topup_by_channel.csv": ["channel", "transactions", "percent_transactions", "amount_baht", "percent_amount"],
    "24_card_status_detail.csv": ["status_group", "status_name", "bem_count", "exat_count", "total_count", "percent"],
    "25_card_inactive_balance.csv": ["amount_range", "card_count", "amount_baht"],
    "26_anomaly_by_route.csv": ["route_name", "total_events", "cause_install", "cause_no_entry_data", "cause_low_balance", "cause_blacklist", "cause_equipment", "cause_other"],
    "27_anomaly_cause_breakdown.csv": ["cause_name", "cause_name_en", "count", "percentage", "category"],
}

TOPIC_LABELS = {k: k for k in REQUIRED_COLUMNS.keys()}

# ----------------------------------------------------------------------------
# SIDEBAR — UPLOAD CSV
# ----------------------------------------------------------------------------
uploaded_map = {}
if is_admin:
    st.sidebar.subheader("📂 นำเข้าข้อมูล CSV (ถาวร)")
    uploaded_files = st.sidebar.file_uploader("เลือกไฟล์ CSV", type="csv", accept_multiple_files=True, key="csv_uploader_persistent")
    if uploaded_files:
        st.sidebar.markdown("**กำหนดปลายทางของแต่ละไฟล์:**")
        dataset_keys = list(REQUIRED_COLUMNS.keys())
        for i, f in enumerate(uploaded_files):
            guess_index = dataset_keys.index(f.name) if f.name in dataset_keys else 0
            target = st.sidebar.selectbox(f"📄 `{f.name}` →", dataset_keys, index=guess_index,
                                           format_func=lambda x: f"{x}  ({TOPIC_LABELS.get(x, x)})",
                                           key=f"map_select_{i}_{f.name}")
            uploaded_map[target] = f
        if st.sidebar.button("💾 บันทึกและแทนที่ไฟล์ลงระบบถาวร", type="primary", use_container_width=True):
            try:
                for target_fname, uploaded_file in uploaded_map.items():
                    dest_path = DATA_DIR / target_fname
                    with open(dest_path, "wb") as f_out:
                        f_out.write(uploaded_file.getbuffer())
                append_audit(user["name"], "อัปโหลดและแทนที่ไฟล์ CSV ถาวร", {"จำนวนไฟล์": len(uploaded_map)})
                st.cache_data.clear()
                st.sidebar.success("✅ บันทึกไฟล์ลงดิสก์เรียบร้อยแล้ว!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"เกิดข้อผิดพลาด: {e}")
else:
    st.sidebar.info("🔒 การนำเข้าข้อมูล CSV จำกัดสิทธิ์เฉพาะ Admin")


@st.cache_data(show_spinner=False)
def load_and_validate_v2(filename: str):
    required = REQUIRED_COLUMNS[filename]
    file_path = DATA_DIR / filename
    try:
        if not file_path.exists():
            return pd.DataFrame(columns=required), {"ไฟล์": filename, "แถว": 0, "สถานะ": "ERROR", "หมายเหตุ": "ไม่พบไฟล์"}
        df = pd.read_csv(file_path)
        missing = [c for c in required if c not in df.columns]
        if missing:
            return df, {"ไฟล์": filename, "แถว": len(df), "สถานะ": "ERROR", "หมายเหตุ": f"ขาดคอลัมน์: {', '.join(missing)}"}
        if df.empty:
            return df, {"ไฟล์": filename, "แถว": 0, "สถานะ": "ERROR", "หมายเหตุ": "ไฟล์ว่างเปล่า"}
        if "month" in df.columns:
            df = df.sort_values("month").reset_index(drop=True)
        return df, {"ไฟล์": filename, "แถว": len(df), "สถานะ": "OK", "หมายเหตุ": "โครงสร้างถูกต้อง"}
    except Exception as e:
        return pd.DataFrame(columns=required), {"ไฟล์": filename, "แถว": 0, "สถานะ": "ERROR", "หมายเหตุ": f"อ่านไม่สำเร็จ: {e}"}


# ----------------------------------------------------------------------------
# LOAD ALL DATASETS
# ----------------------------------------------------------------------------
data_log = []
loaded = {}
for fname in REQUIRED_COLUMNS.keys():
    df, meta = load_and_validate_v2(fname)
    loaded[fname] = df
    data_log.append(meta)

validation_df = pd.DataFrame(data_log)
n_ok = (validation_df["สถานะ"] == "OK").sum()
n_error = (validation_df["สถานะ"] == "ERROR").sum()

reg = loaded["01_card_registration.csv"]
inv = loaded["02_card_inventory.csv"]
etc = loaded["03_traffic_etc_overview.csv"]
route = loaded["04_traffic_etc_by_route.csv"]
anomaly = loaded["05_anomaly_events.csv"]
emv = loaded["06_emv_traffic.csv"]
motorway = loaded["07_motorway_tollway.csv"]
topup_total = loaded["08_topup_total.csv"]
topup_edc = loaded["09_topup_edc.csv"]
topup_ext = loaded["10_topup_external_agencies.csv"]
topup_digital = loaded["11_topup_digital_channel.csv"]
website = loaded["12_website_stats.csv"]
card_status = loaded["13_card_status.csv"]
cs = loaded["14_customer_service.csv"]
traffic_4w = loaded["15_traffic_4wheel_etc.csv"]
route_detail = loaded["16_route_transactions_detail.csv"]
tollway_detail = loaded["17_tollway_section_detail.csv"]
annual_summary = loaded["18_annual_cumulative_summary.csv"]
reg_by_route = loaded["19_card_registration_by_route.csv"]
inv_by_route = loaded["20_card_inventory_by_route.csv"]
traffic_full = loaded["21_traffic_etc_by_route_full.csv"]
mpass_detail = loaded["22_route_mpass_easypass.csv"]
topup_channel = loaded["23_topup_by_channel.csv"]
card_detail = loaded["24_card_status_detail.csv"]
inactive_bal = loaded["25_card_inactive_balance.csv"]
anomaly_by_route = loaded["26_anomaly_by_route.csv"]
anomaly_cause = loaded["27_anomaly_cause_breakdown.csv"]

LATEST_MONTH = reg["month_label"].iloc[-1] if (n_error == 0 and not reg.empty) else "ไม่ทราบ"

# ----------------------------------------------------------------------------
# EARLY WARNING THRESHOLDS — แบ่งเป็น 4 กลุ่มตามลักษณะของตัวชี้วัด
#   A) Fixed        — ค่าคงที่ อิง supply chain / regulatory
#   B) Seasonal YoY — เทียบปีต่อปี จับฤดูกาล
#   C) Trend        — เบี่ยงจาก rolling avg 3 เดือน
#   D) Ratio        — อัตราส่วนโครงสร้าง
#   (legacy)        — MoM fallback เมื่อข้อมูลไม่พอสำหรับ YoY/Trend
# ----------------------------------------------------------------------------
default_th = dict(
    # ===== กลุ่ม A: Fixed =====
    obu_warn=180000, obu_crit=150000,
    sc_warn=150000,  sc_crit=120000,
    lost_value_warn_baht=3_000_000,    lost_value_crit_baht=5_000_000,
    inactive_bal_warn_baht=15_000_000, inactive_bal_crit_baht=25_000_000,
    obu_days_warn=90, obu_days_crit=60,

    # ===== กลุ่ม B: Seasonal (YoY, %) =====
    reg_yoy_warn=-10.0,     reg_yoy_crit=-20.0,
    topup_yoy_warn=-7.0,    topup_yoy_crit=-15.0,
    anom_yoy_warn=15.0,     anom_yoy_crit=30.0,
    cs_yoy_warn=15.0,       cs_yoy_crit=30.0,
    traffic_yoy_warn=-8.0,  traffic_yoy_crit=-15.0,
    website_yoy_warn=-15.0, website_yoy_crit=-25.0,

    # ===== กลุ่ม C: Trend (pp / %) =====
    etc_trend_warn_pp=-0.8,   etc_trend_crit_pp=-1.5,
    emv_trend_warn_pp=-0.5,   emv_trend_crit_pp=-1.0,
    active_mom_warn=-1.5,     active_mom_crit=-3.0,
    digital_trend_warn=-20.0, digital_trend_crit=-35.0,

    # ===== กลุ่ม D: Ratio (%) =====
    lost_ratio_warn=0.30,      lost_ratio_crit=0.50,
    suspended_ratio_warn=4.0,  suspended_ratio_crit=7.0,
    lowbal_ratio_warn=12.0,    lowbal_ratio_crit=18.0,
    mpass_shift_warn=3.0,      mpass_shift_crit=5.0,

    # ===== Legacy MoM fallback (เก็บไว้เพื่อ backward compatibility) =====
    reg_warn=15, reg_crit=30,
    anom_warn=5, anom_crit=10,
    topup_warn=5, topup_crit=10,
    lost_warn=5, lost_crit=10,
    cs_warn=5, cs_crit=10,
    etc_warn=1.5, etc_crit=2.5,
)
current_th = {k: saved_th.get(k, default_th[k]) for k in default_th}

if is_admin:
    with st.sidebar.expander("⚙️ ตั้งค่าเกณฑ์ Early Warning (ถาวร)", expanded=False):
        st.caption("⚠️ บันทึกถาวรลงดิสก์ ไม่หายเมื่อ Logout")
        tA, tB, tC, tD = st.tabs(["A Fixed", "B YoY", "C Trend", "D Ratio"])

        with st.form("settings_form_v2"):
            with tA:
                st.markdown("**กลุ่ม A — ค่าคงที่ (Supply/Regulatory)**")
                p_obu_warn = st.number_input("OBU เตือน (ใบ)", value=int(current_th["obu_warn"]), step=10000)
                p_obu_crit = st.number_input("OBU วิกฤต (ใบ)", value=int(current_th["obu_crit"]), step=10000)
                p_sc_warn  = st.number_input("Smart Card เตือน (ใบ)", value=int(current_th["sc_warn"]), step=10000)
                p_sc_crit  = st.number_input("Smart Card วิกฤต (ใบ)", value=int(current_th["sc_crit"]), step=10000)
                p_lv_warn  = st.number_input("มูลค่าบัตรหาย เตือน (บาท)", value=int(current_th["lost_value_warn_baht"]), step=100000)
                p_lv_crit  = st.number_input("มูลค่าบัตรหาย วิกฤต (บาท)", value=int(current_th["lost_value_crit_baht"]), step=100000)
                p_ib_warn  = st.number_input("Inactive balance เตือน (บาท)", value=int(current_th["inactive_bal_warn_baht"]), step=1000000)
                p_ib_crit  = st.number_input("Inactive balance วิกฤต (บาท)", value=int(current_th["inactive_bal_crit_baht"]), step=1000000)

            with tB:
                st.markdown("**กลุ่ม B — Seasonal YoY (%)**")
                p_reg_yoy_w   = st.slider("สมัครใหม่ YoY เตือน (%)", -50, 0, int(current_th["reg_yoy_warn"]))
                p_reg_yoy_c   = st.slider("สมัครใหม่ YoY วิกฤต (%)", -60, -10, int(current_th["reg_yoy_crit"]))
                p_topup_yoy_w = st.slider("ยอดเติมเงิน YoY เตือน (%)", -40, 0, int(current_th["topup_yoy_warn"]))
                p_topup_yoy_c = st.slider("ยอดเติมเงิน YoY วิกฤต (%)", -50, -5, int(current_th["topup_yoy_crit"]))
                p_anom_yoy_w  = st.slider("Anomaly YoY เตือน (%)", 0, 50, int(current_th["anom_yoy_warn"]))
                p_anom_yoy_c  = st.slider("Anomaly YoY วิกฤต (%)", 10, 100, int(current_th["anom_yoy_crit"]))
                p_cs_yoy_w    = st.slider("CS YoY เตือน (%)", 0, 50, int(current_th["cs_yoy_warn"]))
                p_cs_yoy_c    = st.slider("CS YoY วิกฤต (%)", 10, 100, int(current_th["cs_yoy_crit"]))

            with tC:
                st.markdown("**กลุ่ม C — Trend (เบี่ยงจาก rolling avg 3 เดือน)**")
                p_etc_w = st.slider("ETC trend เตือน (pp)", -5.0, 0.0, float(current_th["etc_trend_warn_pp"]), 0.1)
                p_etc_c = st.slider("ETC trend วิกฤต (pp)", -8.0, -0.5, float(current_th["etc_trend_crit_pp"]), 0.1)
                p_emv_w = st.slider("EMV trend เตือน (pp)", -3.0, 0.0, float(current_th["emv_trend_warn_pp"]), 0.1)
                p_emv_c = st.slider("EMV trend วิกฤต (pp)", -5.0, -0.5, float(current_th["emv_trend_crit_pp"]), 0.1)
                p_act_w = st.slider("Active card MoM เตือน (%)", -10.0, 0.0, float(current_th["active_mom_warn"]), 0.1)
                p_act_c = st.slider("Active card MoM วิกฤต (%)", -15.0, -1.0, float(current_th["active_mom_crit"]), 0.1)

            with tD:
                st.markdown("**กลุ่ม D — Ratio (%)**")
                p_lr_w = st.slider("Lost/Active เตือน (%)", 0.0, 2.0, float(current_th["lost_ratio_warn"]), 0.05)
                p_lr_c = st.slider("Lost/Active วิกฤต (%)", 0.1, 3.0, float(current_th["lost_ratio_crit"]), 0.05)
                p_sr_w = st.slider("Suspended/Total เตือน (%)", 0.0, 15.0, float(current_th["suspended_ratio_warn"]), 0.5)
                p_sr_c = st.slider("Suspended/Total วิกฤต (%)", 1.0, 20.0, float(current_th["suspended_ratio_crit"]), 0.5)
                p_lb_w = st.slider("LowBalance/Active เตือน (%)", 0.0, 30.0, float(current_th["lowbal_ratio_warn"]), 0.5)
                p_lb_c = st.slider("LowBalance/Active วิกฤต (%)", 5.0, 40.0, float(current_th["lowbal_ratio_crit"]), 0.5)

            submitted_th = st.form_submit_button("💾 บันทึกเกณฑ์ทั้งหมด", type="primary", use_container_width=True)
            if submitted_th:
                new_values = dict(
                    obu_warn=p_obu_warn, obu_crit=p_obu_crit,
                    sc_warn=p_sc_warn, sc_crit=p_sc_crit,
                    lost_value_warn_baht=p_lv_warn, lost_value_crit_baht=p_lv_crit,
                    inactive_bal_warn_baht=p_ib_warn, inactive_bal_crit_baht=p_ib_crit,
                    reg_yoy_warn=p_reg_yoy_w, reg_yoy_crit=p_reg_yoy_c,
                    topup_yoy_warn=p_topup_yoy_w, topup_yoy_crit=p_topup_yoy_c,
                    anom_yoy_warn=p_anom_yoy_w, anom_yoy_crit=p_anom_yoy_c,
                    cs_yoy_warn=p_cs_yoy_w, cs_yoy_crit=p_cs_yoy_c,
                    etc_trend_warn_pp=p_etc_w, etc_trend_crit_pp=p_etc_c,
                    emv_trend_warn_pp=p_emv_w, emv_trend_crit_pp=p_emv_c,
                    active_mom_warn=p_act_w, active_mom_crit=p_act_c,
                    lost_ratio_warn=p_lr_w, lost_ratio_crit=p_lr_c,
                    suspended_ratio_warn=p_sr_w, suspended_ratio_crit=p_sr_c,
                    lowbal_ratio_warn=p_lb_w, lowbal_ratio_crit=p_lb_c,
                )
                update_thresholds(new_values, username=user["name"])
                st.cache_data.clear()
                st.success("✅ บันทึกเกณฑ์ถาวรสำเร็จ!")
                st.rerun()

        if st.button("🔄 คืนค่าเกณฑ์เริ่มต้น", use_container_width=True):
            reset_thresholds_to_default(username=user["name"])
            st.cache_data.clear()
            st.warning("คืนค่าเกณฑ์เริ่มต้นแล้ว")
            st.rerun()

    with st.sidebar.expander("🔐 Login Audit Log", expanded=False):
        log_df = get_audit_log()
        if log_df is not None and not log_df.empty:
            st.dataframe(log_df.tail(20), use_container_width=True, hide_index=True)
        else:
            st.caption("ยังไม่มีบันทึกการเข้าใช้งาน")

    with st.sidebar.expander("📋 ตารางสิทธิ์การเข้าถึงระบบ (RBAC)", expanded=False):
        rbac_df = pd.DataFrame({
            "ฟังก์ชัน": ["ภาพรวม", "แท็บรายละเอียด", "ยอดสะสมปีงบ", "Early Warning", "ปรับเกณฑ์ถาวร", "อัปโหลด CSV", "Export PDF", "Audit Log"],
            "Admin": ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅"],
            "ผู้ว่าการ": ["✅", "❌", "✅", "✅", "❌", "❌", "✅", "❌"],
            "ผู้บริหาร": ["✅", "✅", "✅", "✅", "❌", "❌", "✅", "❌"],
            "เจ้าหน้าที่": ["✅", "✅", "✅", "✅", "❌", "❌", "❌", "❌"],
        })
        st.dataframe(rbac_df, use_container_width=True, hide_index=True)

th_reg_warn = current_th["reg_warn"]; th_reg_crit = current_th["reg_crit"]
th_anom_warn = current_th["anom_warn"]; th_anom_crit = current_th["anom_crit"]
th_topup_warn = current_th["topup_warn"]; th_topup_crit = current_th["topup_crit"]
th_lost_warn = current_th["lost_warn"]; th_lost_crit = current_th["lost_crit"]
th_obu_warn = current_th["obu_warn"]; th_obu_crit = current_th["obu_crit"]
th_sc_warn = current_th["sc_warn"]; th_sc_crit = current_th["sc_crit"]
th_cs_warn = current_th["cs_warn"]; th_cs_crit = current_th["cs_crit"]
th_etc_warn = current_th["etc_warn"]; th_etc_crit = current_th["etc_crit"]
th_lost_value_warn = current_th["lost_value_warn_baht"]
th_lost_value_crit = current_th["lost_value_crit_baht"]
th_inactive_warn = current_th["inactive_bal_warn_baht"]
th_inactive_crit = current_th["inactive_bal_crit_baht"]
th_obu_days_warn = current_th["obu_days_warn"]
th_obu_days_crit = current_th["obu_days_crit"]
th_reg_yoy_warn = current_th["reg_yoy_warn"]; th_reg_yoy_crit = current_th["reg_yoy_crit"]
th_topup_yoy_warn = current_th["topup_yoy_warn"]; th_topup_yoy_crit = current_th["topup_yoy_crit"]
th_anom_yoy_warn = current_th["anom_yoy_warn"]; th_anom_yoy_crit = current_th["anom_yoy_crit"]
th_cs_yoy_warn = current_th["cs_yoy_warn"]; th_cs_yoy_crit = current_th["cs_yoy_crit"]
th_etc_trend_warn = current_th["etc_trend_warn_pp"]; th_etc_trend_crit = current_th["etc_trend_crit_pp"]
th_emv_trend_warn = current_th["emv_trend_warn_pp"]; th_emv_trend_crit = current_th["emv_trend_crit_pp"]
th_active_mom_warn = current_th["active_mom_warn"]; th_active_mom_crit = current_th["active_mom_crit"]
th_lost_ratio_warn = current_th["lost_ratio_warn"]; th_lost_ratio_crit = current_th["lost_ratio_crit"]
th_sus_ratio_warn  = current_th["suspended_ratio_warn"]; th_sus_ratio_crit = current_th["suspended_ratio_crit"]
th_lowbal_ratio_warn = current_th["lowbal_ratio_warn"]; th_lowbal_ratio_crit = current_th["lowbal_ratio_crit"]

st.sidebar.markdown("---")
st.sidebar.caption(f"📅 ข้อมูลล่าสุด: เดือน {LATEST_MONTH} | ปีงบประมาณ 2569")
st.sidebar.caption(f"🕒 โหลดระบบเมื่อ: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def pct_change(curr, prev):
    return 0.0 if prev == 0 else (curr - prev) / prev * 100

def safe_pct(num, den):
    return 0.0 if den == 0 else num / den * 100

def status_from_pct(change, warn_th, crit_th, bad_direction="increase"):
    if bad_direction == "increase":
        if change >= crit_th: return "CRITICAL"
        elif change >= warn_th: return "WARNING"
        return "NORMAL"
    else:
        if change <= -crit_th: return "CRITICAL"
        elif change <= -warn_th: return "WARNING"
        return "NORMAL"

def status_from_abs(value, warn_th, crit_th):
    if value < crit_th: return "CRITICAL"
    elif value < warn_th: return "WARNING"
    return "NORMAL"

def yoy_change(df, col, month_col="month"):
    """
    คำนวณ YoY % change ของเดือนล่าสุดเทียบเดือนเดียวกันของปีก่อน
    คืนค่า None ถ้าข้อมูลไม่ถึง 13 เดือน
    """
    if df is None or df.empty or col not in df.columns or month_col not in df.columns:
        return None
    try:
        s = df[[month_col, col]].copy()
        s[month_col] = s[month_col].astype(str)
        curr_month = s[month_col].iloc[-1]
        # หาเดือนเดียวกันของปีก่อน (YYYY-MM → YYYY-1-MM)
        try:
            y, m = curr_month.split("-")
            prev_label = f"{int(y)-1}-{m}"
        except Exception:
            return None
        prev_row = s[s[month_col] == prev_label]
        if prev_row.empty:
            return None
        curr_v = float(s[col].iloc[-1])
        prev_v = float(prev_row[col].iloc[0])
        if prev_v == 0:
            return None
        return (curr_v - prev_v) / prev_v * 100
    except Exception:
        return None


def trend_gap(df, col, window=3):
    """
    คืนค่า (latest - rolling_mean_before_latest) — ใช้จับว่าค่าเบี่ยงจาก trend แค่ไหน
    rolling เฉลี่ย window งวดก่อนหน้าล่าสุด ไม่รวมค่าล่าสุด เพื่อไม่ให้ trend ถูกดึงด้วย outlier
    """
    if df is None or df.empty or col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) < window + 1:
        return None
    baseline = s.iloc[-(window+1):-1].mean()   # 3 งวดก่อนล่าสุด
    return float(s.iloc[-1] - baseline)

def _trend_stats(df, col, window=3):
    """
    คืนค่า (latest, baseline, gap, gap_pct) สำหรับ trend analysis
      - baseline = rolling mean ของ window งวด "ก่อนหน้า" ล่าสุด (ไม่รวมค่าล่าสุด)
      - gap      = latest - baseline  (absolute)
      - gap_pct  = (latest - baseline) / baseline × 100  (หรือ None ถ้า baseline=0)
    คืน (None, None, None, None) ถ้าข้อมูลไม่พอ
    """
    if df is None or df.empty or col not in df.columns:
        return None, None, None, None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) < window + 1:
        return None, None, None, None
    baseline = s.iloc[-(window + 1):-1].mean()
    latest = s.iloc[-1]
    gap = float(latest - baseline)
    gap_pct = float((latest - baseline) / baseline * 100) if baseline != 0 else None
    return float(latest), float(baseline), gap, gap_pct

def status_from_trend(gap, warn_pp, crit_pp):
    """gap = ค่าล่าสุด - rolling avg. warn/crit เป็นค่าลบ (เช่น -0.8, -1.5)"""
    if gap is None:
        return "N/A"
    if gap <= crit_pp: return "CRITICAL"
    if gap <= warn_pp: return "WARNING"
    return "NORMAL"


def status_from_ratio(value, warn_th, crit_th):
    """อัตราส่วน — ยิ่งมากยิ่งแย่"""
    if value is None:
        return "N/A"
    if value >= crit_th: return "CRITICAL"
    if value >= warn_th: return "WARNING"
    return "NORMAL"


def status_label_safe(status):
    """คืน badge รองรับ N/A"""
    return {
        "CRITICAL": "🔴 วิกฤต",
        "WARNING":  "🟠 เฝ้าระวัง",
        "NORMAL":   "🟢 ปกติ",
        "N/A":      "⚪ ไม่มีข้อมูล",
    }.get(status, "⚪ ไม่มีข้อมูล")

def badge(status):
    return {
        "CRITICAL": "🔴 วิกฤต", "WARNING": "🟠 เฝ้าระวัง",
        "NORMAL":   "🟢 ปกติ", "N/A":     "⚪ ไม่มีข้อมูล",
    }.get(status, "⚪ ไม่มีข้อมูล")

def kpi_tile(label, value, delta="", color="blue", delta_dir=None):
    if delta_dir is None:
        delta_dir = "up" if (isinstance(delta, str) and delta.startswith("+")) else "down" if (isinstance(delta, str) and delta.startswith("-")) else "flat"
    return f"""
    <div class="kpi-tile {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta {delta_dir}">{delta}</div>
    </div>
    """

def section_title(text, page_tag="", scope_tag=""):
    ptag = f'<span class="pdf-page-tag">{page_tag}</span>' if page_tag else ""
    stag = f'<span class="scope-tag">{scope_tag}</span>' if scope_tag else ""
    return f'<div class="section-title">{text}{ptag}{stag}</div>'

def sub_section_title(text, page_tag=""):
    tag = f'<span class="pdf-page-tag">{page_tag}</span>' if page_tag else ""
    return f'<div class="sub-section-title">{text}{tag}</div>'


def latest_pair(df, col):
    """Return latest and previous numeric values safely."""
    if df is None or df.empty or col not in df.columns:
        return None, None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) == 0:
        return None, None
    return float(s.iloc[-1]), float(s.iloc[-2]) if len(s) > 1 else None

def month_days(df, month_col="month"):
    """Number of calendar days for the latest month, without hard-coding 30/31."""
    if df is None or df.empty or month_col not in df.columns:
        return 30
    try:
        last = pd.to_datetime(str(df[month_col].iloc[-1]) + "-01")
        return int(last.days_in_month)
    except Exception:
        return 30

def direction_text(change, up_good=False, unit="%"):
    if change is None:
        return "ยังไม่มีข้อมูลเปรียบเทียบ"
    if abs(change) < 0.01:
        return "ทรงตัวเมื่อเทียบกับเดือนก่อน"
    if change > 0:
        return f"เพิ่มขึ้น {change:+.1f}{unit}"
    return f"ลดลง {abs(change):.1f}{unit}"

def interpret_change(curr, prev, metric_name, unit="", decimals=0, neutral=1.0):
    """Descriptive interpretation only; no policy/action recommendation."""
    if curr is None:
        return f"{metric_name}: ไม่มีข้อมูลเพียงพอสำหรับการตีความ"
    curr_s = f"{curr:,.{decimals}f}"
    if prev is None:
        return f"{metric_name} เดือนล่าสุดอยู่ที่ {curr_s}{unit} และยังไม่มีเดือนก่อนหน้าให้ใช้เปรียบเทียบ"
    chg = pct_change(curr, prev)
    if abs(chg) < neutral:
        phrase = "ทรงตัว"
    elif chg > 0:
        phrase = f"เพิ่มขึ้น {chg:.1f}%"
    else:
        phrase = f"ลดลง {abs(chg):.1f}%"
    return f"{metric_name} เดือนล่าสุด {curr_s}{unit} — {phrase} เมื่อเทียบกับเดือนก่อน"

def html_interpretation(title, bullets, note=None):
    items = "".join(f"<li>{b}</li>" for b in bullets if b)
    note_html = f'<div style="margin-top:10px;font-size:12px;color:#666;">{note}</div>' if note else ""
    return f"""
    <div class="exec-summary-box" style="border-left-color:#0288D1;">
        <h4>💡 {title}</h4>
        <ul>{items}</ul>
        {note_html}
    </div>
    """

def trend_shape(df, col):
    """Classify the latest movement using the last 3 observations."""
    if df is None or df.empty or col not in df.columns:
        return "insufficient"
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) < 2:
        return "insufficient"
    if len(s) < 3:
        return "up" if s.iloc[-1] > s.iloc[-2] else "down" if s.iloc[-1] < s.iloc[-2] else "flat"
    a, b, c = s.iloc[-3], s.iloc[-2], s.iloc[-1]
    if c > b > a:
        return "up"
    if c < b < a:
        return "down"
    if (c > b and b < a) or (c < b and b > a):
        return "turn"
    return "flat"

def share_of_total(value, total):
    return safe_pct(value, total)

def fmt_million(v):
    return f"{v/1e6:,.2f} ลบ."

def fmt_billion(v):
    return f"{v/1e9:,.2f} พันล้าน"

def build_stock_interpretation(obu_state, sc_state, obu_burn, sc_burn, obu_to_crit, sc_to_crit,
                               obu_now, sc_now, th_obu_warn, th_obu_crit, th_sc_warn, th_sc_crit):
    bullets = []
    def stock_phrase(name, now, burn, warn, crit, tocrit, state):
        if state == "CRITICAL":
            return f"<b>{name}</b> อยู่ต่ำกว่าเกณฑ์วิกฤตที่กำหนด ({now:,.0f} ใบ) สะท้อนระดับคงคลังปัจจุบันที่ต่ำเมื่อเทียบกับ threshold"
        if state == "WARNING":
            return f"<b>{name}</b> อยู่ในช่วงเฝ้าระวัง ({now:,.0f} ใบ) และต่ำกว่าเกณฑ์เตือน {warn:,.0f} ใบ"
        if burn > 0:
            return f"<b>{name}</b> ยังสูงกว่าเกณฑ์เตือน ({now:,.0f} ใบ) โดยแนวโน้มย้อนหลังสะท้อนการลดลงเฉลี่ยประมาณ {burn:,.0f} ใบ/เดือน"
        return f"<b>{name}</b> อยู่ในระดับปกติ ({now:,.0f} ใบ) และยังไม่เห็นการลดลงต่อเนื่องจากข้อมูลย้อนหลัง"
    bullets.append(stock_phrase("OBU", obu_now, obu_burn, th_obu_warn, th_obu_crit, obu_to_crit, obu_state))
    bullets.append(stock_phrase("Smart Card", sc_now, sc_burn, th_sc_warn, th_sc_crit, sc_to_crit, sc_state))
    if obu_burn > 0 and sc_burn > 0:
        ratio = obu_burn / sc_burn if sc_burn else 0
        bullets.append(f"อัตราการลดลงเฉลี่ยของ OBU เทียบกับ Smart Card อยู่ที่ประมาณ {ratio:.2f} เท่าในช่วงข้อมูลที่ใช้คำนวณ")
    bullets.append("ระยะเวลาที่คาดว่าจะถึง threshold เป็นการประมาณเชิงเส้นจากแนวโน้มย้อนหลัง ไม่ใช่การพยากรณ์ความต้องการในอนาคต")
    return html_interpretation("Interpretation — คงคลังบัตร", bullets)

def build_stock_recommendation(*args, **kwargs):
    return ""


# ----------------------------------------------------------------------------
# BUILD ALERTS — ครอบคลุม 4 กลุ่มเกณฑ์
# ----------------------------------------------------------------------------
alerts = []

def _add_alert(title, latest_s, prev_s, change_s, status, advice, group=""):
    alerts.append({
        "กลุ่ม":     group,
        "หัวข้อ":    title,
        "ค่าล่าสุด": latest_s,
        "เดือนก่อน": prev_s,
        "เปลี่ยนแปลง": change_s,
        "สถานะ":     status,
        "คำแนะนำ":   advice,
    })

if n_error == 0:
    # ============================================================
    # กลุ่ม A — Fixed
    # ============================================================
    obu_v = inv["obu_stock"].iloc[-1]
    sc_v  = inv["smartcard_stock"].iloc[-1]
    _add_alert("คงคลังบัตร OBU", f"{obu_v:,.0f} ใบ", "—",
               f"เกณฑ์ เตือน {th_obu_warn:,.0f} / วิกฤต {th_obu_crit:,.0f}",
               status_from_abs(obu_v, th_obu_warn, th_obu_crit),
               "วางแผนจัดซื้อ OBU เพิ่มล่วงหน้า", "A")

    _add_alert("คงคลังบัตร Smart Card", f"{sc_v:,.0f} ใบ", "—",
               f"เกณฑ์ เตือน {th_sc_warn:,.0f} / วิกฤต {th_sc_crit:,.0f}",
               status_from_abs(sc_v, th_sc_warn, th_sc_crit),
               "วางแผนจัดซื้อ Smart Card เพิ่ม", "A")

    # มูลค่าบัตรหาย
    lv = card_status["lost_value_baht"].iloc[-1]
    _add_alert("มูลค่าบัตรสูญหาย (บาท)", f"{lv/1e6:,.2f} ลบ.", "—",
               f"เกณฑ์ เตือน {th_lost_value_warn/1e6:.1f} / วิกฤต {th_lost_value_crit/1e6:.1f} ลบ.",
               status_from_pct(lv, th_lost_value_warn, th_lost_value_crit, "increase"),
               "ทบทวนกระบวนการอายัดบัตรและเรียกคืนเงินคงเหลือ", "A")

    # Inactive balance
    if not inactive_bal.empty:
        ib_row = inactive_bal[inactive_bal["amount_range"].astype(str).str.contains("รวม", na=False)]
        if not ib_row.empty:
            ib_v = ib_row["amount_baht"].iloc[0]
            _add_alert("เงินคงเหลือไม่เคลื่อนไหว >2 ปี", f"{ib_v/1e6:,.1f} ลบ.", "—",
                       f"เกณฑ์ เตือน {th_inactive_warn/1e6:.0f} / วิกฤต {th_inactive_crit/1e6:.0f} ลบ.",
                       status_from_pct(ib_v, th_inactive_warn, th_inactive_crit, "increase"),
                       "พิจารณาแนวทางคืนเงิน/มาตรการตามกฎหมาย", "A")

    # OBU days-of-supply — ต้องมีข้อมูล ≥ 2 งวดจึงประมาณ burn rate ได้
    try:
        n_m = len(inv)
        if n_m >= 2:
            obu_burn_m = (inv["obu_stock"].iloc[0] - inv["obu_stock"].iloc[-1]) / (n_m - 1)
            obu_now_val = inv["obu_stock"].iloc[-1]
            if obu_burn_m > 0:
                obu_days_left = obu_now_val / obu_burn_m * 30
                obu_dos_status = (
                    "CRITICAL" if obu_days_left < th_obu_days_crit
                    else "WARNING" if obu_days_left < th_obu_days_warn
                    else "NORMAL"
                )
                _add_alert(
                    "อายุคงคลัง OBU (days of supply)",
                    f"{obu_days_left:,.0f} วัน",
                    "—",
                    f"เกณฑ์ เตือน {th_obu_days_warn} / วิกฤต {th_obu_days_crit} วัน",
                    obu_dos_status,
                    "วางแผนจัดซื้อ OBU ล่วงหน้าตาม lead time (ประมาณจาก burn rate)",
                    "A",
                )
            else:
                _add_alert("อายุคงคลัง OBU (days of supply)", "—", "—",
                           "burn rate ≤ 0 — ไม่สามารถประมาณได้", "N/A",
                           "ตรวจสอบข้อมูลคงคลัง", "A")
        else:
            _add_alert("อายุคงคลัง OBU (days of supply)", "—", "—",
                       "ข้อมูลไม่ถึง 2 งวด", "N/A",
                       "รอข้อมูลเพิ่มเติม", "A")
    except Exception:
        pass

    # ============================================================
    # กลุ่ม B — Seasonal YoY (ถ้าข้อมูลไม่ถึง 13 เดือน → N/A)
    # ============================================================
    def _add_yoy_alert(title, df, col, warn, crit, unit, good_up, advice):
        """
        YoY alert — normalize threshold ให้เป็นบวกเสมอ
        เพราะ status_from_pct ใช้สูตร -warn_th / -crit_th
        """
        warn_pos = abs(warn)
        crit_pos = abs(crit)

        yoy = yoy_change(df, col)
        if yoy is None:
            _add_alert(title + " (YoY)", "—", "—",
                    "ข้อมูลไม่ถึง 13 เดือน", "N/A", advice, "B")
            return

        curr = df[col].iloc[-1]
        _add_alert(
            title + " (YoY)",
            f"{curr:,.0f} {unit}",
            "ปีก่อน —",
            f"{yoy:+.1f}%",
            status_from_pct(
                yoy,
                warn_pos,
                crit_pos,
                "increase" if not good_up else "decrease",
            ),
            advice, "B",
        )

    _add_yoy_alert("ยอดสมัครใช้บัตร", reg, "new_registrations",
               th_reg_yoy_warn, th_reg_yoy_crit,     # ← ส่งค่าลบตรง ๆ
               "บัตร", True, "ติดตามแคมเปญการตลาด")

    _add_yoy_alert("ยอดเติมเงินสำรอง", topup_total, "total_baht",
                th_topup_yoy_warn, th_topup_yoy_crit,
                "บาท", True, "ตรวจสอบช่องทางเติมเงิน")

    _add_yoy_alert("เหตุการณ์ไม้กั้นไม่เปิด", anomaly, "total_events",
                th_anom_yoy_warn, th_anom_yoy_crit,
                "ครั้ง", False, "ตรวจสอบอุปกรณ์ ETC")

    _add_yoy_alert("เรื่องร้องเรียน CS", cs, "total_cases",
                th_cs_yoy_warn, th_cs_yoy_crit,
                "เรื่อง", False, "วิเคราะห์สาเหตุเรื่องร้องเรียน")

    # traffic — ใช้ current_th ตรง ๆ แทน dir() hack
    _add_yoy_alert("ปริมาณจราจรรวม", etc, "total_traffic_million",
                current_th["traffic_yoy_warn"], current_th["traffic_yoy_crit"],
                "ล้านคัน", True, "ตรวจสอบสถานการณ์จราจร")

    _add_yoy_alert("ผู้เข้าเว็บไซต์", website, "avg_daily_visits",
                current_th["website_yoy_warn"], current_th["website_yoy_crit"],
                "ครั้ง/วัน", True, "ตรวจสอบ SEO และแคมเปญออนไลน์")

    # ============================================================
    # กลุ่ม C — Trend (rolling avg 3 เดือน)
    # ============================================================
    def _add_trend_alert(title, df, col, warn, crit, unit, advice, mode="pp"):
        """
        mode:
          - "pp"   : gap เป็น percentage point (ใช้กับค่า % ตรง ๆ เช่น ETC%, EMV%)
          - "pct"  : gap% เทียบ baseline (ใช้กับ count/amount เช่น Digital topup)
          - "abs"  : gap absolute (ใช้กับค่าที่มีหน่วยตรง ๆ)
        """
        latest, baseline, gap, gap_pct = _trend_stats(df, col, window=3)

        if latest is None:
            _add_alert(title + " (Trend)", "—", "—",
                       "ข้อมูลไม่ถึง 4 งวด", "N/A", advice, "C")
            return

        if mode == "pp":
            latest_s   = f"{latest:.2f}%"
            baseline_s = f"avg 3 งวดก่อน {baseline:.2f}%"
            gap_s      = f"{gap:+.2f} pp"
            status     = status_from_trend(gap, warn, crit)

        elif mode == "pct":
            latest_s   = f"{latest:,.0f} {unit}".strip()
            baseline_s = f"avg 3 งวดก่อน {baseline:,.0f}"
            if gap_pct is None:
                gap_s  = "—"
                status = "N/A"
            else:
                gap_s  = f"{gap_pct:+.1f}%"
                status = status_from_trend(gap_pct, warn, crit)

        else:  # abs
            latest_s   = f"{latest:,.0f} {unit}".strip()
            baseline_s = f"avg 3 งวดก่อน {baseline:,.0f}"
            gap_s      = f"{gap:+,.0f} {unit}".strip()
            status     = status_from_trend(gap, warn, crit)

        _add_alert(title + " (Trend)", latest_s, baseline_s,
                   gap_s, status, advice, "C")

    _add_trend_alert("สัดส่วน ETC", etc, "etc_percent",
                     th_etc_trend_warn, th_etc_trend_crit, "%",
                     "ตรวจสอบอุปกรณ์ ETC และประสบการณ์ผู้ใช้",
                     mode="pp")
    _add_trend_alert("สัดส่วน EMV", emv, "emv_percent",
                     th_emv_trend_warn, th_emv_trend_crit, "%",
                     "ตรวจสอบการรับชำระ EMV",
                     mode="pp")

    # Active cards MoM
    act_now = card_status["active_cards"].iloc[-1]
    act_prev = card_status["active_cards"].iloc[-2]
    act_chg = pct_change(act_now, act_prev)
    _add_alert("บัตร Active (MoM)",
               f"{act_now:,.0f} ใบ", f"{act_prev:,.0f} ใบ", f"{act_chg:+.1f}%",
               status_from_pct(act_chg, -th_active_mom_warn if th_active_mom_warn < 0 else th_active_mom_warn,
                                -th_active_mom_crit if th_active_mom_crit < 0 else th_active_mom_crit,
                                "decrease"),
               "ตรวจสอบสาเหตุบัตรหลุดจากระบบ", "C")

    # Digital topup trend (EXAT Portal + Website)
    # threshold digital_trend_warn/crit หน่วยเป็น % change
    _add_trend_alert(
        "Digital topup",
        topup_digital, "transactions",
        current_th["digital_trend_warn"],
        current_th["digital_trend_crit"],
        "รายการ",
        "ตรวจสอบช่องทาง EXAT Portal / Website",
        mode="pct",
    )

    # ============================================================
    # กลุ่ม D — Ratio
    # ============================================================
    # Lost / Active
    lost_n = card_status["lost_count"].iloc[-1]
    lost_ratio = safe_pct(lost_n, act_now)
    _add_alert("อัตราบัตรหาย / บัตร Active",
               f"{lost_ratio:.3f}%", "—",
               f"เกณฑ์ เตือน {th_lost_ratio_warn:.2f}% / วิกฤต {th_lost_ratio_crit:.2f}%",
               status_from_ratio(lost_ratio, th_lost_ratio_warn, th_lost_ratio_crit),
               "ทบทวนกระบวนการติดตามบัตรหาย", "D")

    # Suspended / Total
    sus_n = card_status["suspended_cards"].iloc[-1]
    tot_n = act_now + sus_n + card_status["low_balance_cards"].iloc[-1] + lost_n
    sus_ratio = safe_pct(sus_n, tot_n)
    _add_alert("อัตราบัตรถูกระงับ / ทั้งหมด",
               f"{sus_ratio:.2f}%", "—",
               f"เกณฑ์ เตือน {th_sus_ratio_warn:.1f}% / วิกฤต {th_sus_ratio_crit:.1f}%",
               status_from_ratio(sus_ratio, th_sus_ratio_warn, th_sus_ratio_crit),
               "ตรวจสอบสาเหตุการระงับบัตรจำนวนมาก", "D")

    # Low balance / Active
    lb_n = card_status["low_balance_cards"].iloc[-1]
    lb_ratio = safe_pct(lb_n, act_now)
    _add_alert("อัตราเงินเหลือต่ำ / บัตร Active",
               f"{lb_ratio:.2f}%", "—",
               f"เกณฑ์ เตือน {th_lowbal_ratio_warn:.1f}% / วิกฤต {th_lowbal_ratio_crit:.1f}%",
               status_from_ratio(lb_ratio, th_lowbal_ratio_warn, th_lowbal_ratio_crit),
               "กระตุ้นการเติมเงินผ่านช่องทางต่างๆ", "D")

alerts_df = pd.DataFrame(alerts) if alerts else pd.DataFrame(
    columns=["กลุ่ม", "หัวข้อ", "ค่าล่าสุด", "เดือนก่อน", "เปลี่ยนแปลง", "สถานะ", "คำแนะนำ"]
)
n_critical = (alerts_df["สถานะ"] == "CRITICAL").sum() if not alerts_df.empty else 0
n_warning  = (alerts_df["สถานะ"] == "WARNING").sum() if not alerts_df.empty else 0
n_normal   = (alerts_df["สถานะ"] == "NORMAL").sum() if not alerts_df.empty else 0
n_na       = (alerts_df["สถานะ"] == "N/A").sum() if not alerts_df.empty else 0
total_tracked = n_critical + n_warning + n_normal   # ตัด N/A ออกจาก health score

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
user_display = get_user_display(user, ROLE_LABELS[role])
logo_layer = (f'<img class="header-logo" src="data:image/png;base64,{LOGO_B64}" alt="EXAT" />'
              if LOGO_B64 else '<div style="font-size:72px; flex-shrink:0;">🚗</div>')

st.markdown(f"""
<div class="main-header">
    <div class="content">
        <div style="flex:1;">
            <h1>🚗 EASY PASS Executive Dashboard</h1>
            <p>ระบบเก็บค่าผ่านทางพิเศษอัตโนมัติ (Easy Pass) — การทางพิเศษแห่งประเทศไทย (กทพ.)</p>
            <div class="header-meta">
                <span>📅 เดือน: <b>{LATEST_MONTH}</b> &nbsp;|&nbsp; 🗓️ ปีงบประมาณ 2569 &nbsp;|&nbsp; 👤 ผู้ใช้งาน: <b>{user_display}</b></span>
            </div>
        </div>
        {logo_layer}
    </div>
</div>
""", unsafe_allow_html=True)

if n_error > 0:
    st.markdown(f'<div class="import-bad">⚠️ <b>พบปัญหาข้อมูล {n_error} ไฟล์</b> — ตรวจสอบที่แท็บ "📥 จัดการข้อมูล CSV"</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="import-ok">✅ ข้อมูลทั้งหมด {len(REQUIRED_COLUMNS)} ไฟล์ โหลดจากดิสก์ถาวรสำเร็จ</div>', unsafe_allow_html=True)

if is_governor:
    st.markdown('<div class="role-note">👔 มุมมองสำหรับ <b>ผู้ว่าการ</b>: ภาพรวมเชิงกลยุทธ์ ยอดสะสมปีงบประมาณ และศูนย์แจ้งเตือน</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# TABS — ชื่อใหม่ที่สื่อความหมายชัดเจน
# ----------------------------------------------------------------------------
tab_names = ["🏠 ภาพรวมผู้บริหาร"]
if show_operational_tabs:
    tab_names += [
        "🪪 ยอดสมัคร & คงคลังบัตร",
        "🚦 ปริมาณจราจร & ETC",
        "⚠️ ไม้กั้นไม่เปิด",
        "🚗 ธุรกรรม Easy Pass/M-Pass",
        "💰 ยอดเติมเงินสำรอง",
        "🌐 สถิติเว็บไซต์",
        "💳 สถานะบัตรในระบบ",
        "☎️ เรื่องร้องเรียน & CS",
    ]
tab_names += ["📊 ยอดสะสมปีงบ 2569", "🚨 ศูนย์แจ้งเตือน"]
if is_admin:
    tab_names.append("📥 จัดการข้อมูล CSV")
if can_export:
    tab_names.append("📑 ออกรายงาน PDF")

tabs = st.tabs(tab_names)
tab_map = dict(zip(tab_names, tabs))
tab_overview = tab_map["🏠 ภาพรวมผู้บริหาร"]
tab_card = tab_map.get("🪪 ยอดสมัคร & คงคลังบัตร")
tab_traffic = tab_map.get("🚦 ปริมาณจราจร & ETC")
tab_anomaly = tab_map.get("⚠️ ไม้กั้นไม่เปิด")
tab_route_merged = tab_map.get("🚗 ธุรกรรม Easy Pass/M-Pass")
tab_topup = tab_map.get("💰 ยอดเติมเงินสำรอง")
tab_web = tab_map.get("🌐 สถิติเว็บไซต์")
tab_status = tab_map.get("💳 สถานะบัตรในระบบ")
tab_cs = tab_map.get("☎️ เรื่องร้องเรียน & CS")
tab_annual = tab_map["📊 ยอดสะสมปีงบ 2569"]
tab_warning = tab_map["🚨 ศูนย์แจ้งเตือน"]
tab_import = tab_map.get("📥 จัดการข้อมูล CSV")
tab_export = tab_map.get("📑 ออกรายงาน PDF")

# =============================================================================
# TAB: IMPORT (Admin)
# =============================================================================
if is_admin and tab_import is not None:
    with tab_import:
        st.subheader("📥 สถานะการนำเข้าและตรวจสอบไฟล์ข้อมูล CSV")
        c1, c2, c3 = st.columns(3)
        c1.metric("ไฟล์ทั้งหมด", f"{len(REQUIRED_COLUMNS)} ไฟล์")
        c2.metric("โหลดสำเร็จ", f"{n_ok} ไฟล์")
        c3.metric("พบปัญหา", f"{n_error} ไฟล์")

        def hl(r):
            return ["background-color:#D4EDDA" if r["สถานะ"] == "OK" else "background-color:#F8D7DA"] * len(r)

        st.dataframe(validation_df.style.apply(hl, axis=1), use_container_width=True, hide_index=True)
        preview_file = st.selectbox("เลือกไฟล์ดูตัวอย่าง 5 แถวแรก", list(REQUIRED_COLUMNS.keys()))
        st.dataframe(loaded[preview_file].head(5), use_container_width=True)

# =============================================================================
# TAB: ภาพรวมผู้บริหาร
# =============================================================================
with tab_overview:
    # ========================================================
    # EXECUTIVE SUMMARY — Hero Section
    # ========================================================
    if n_error == 0:

        # ---------- Helper: robust keyword matching ----------
        def _find_annual(*patterns):
            """ค้นหา metric ใน annual_summary ด้วยหลาย keyword patterns
            คืน row แรกที่ match หรือ None ถ้าไม่พบ"""
            if annual_summary is None or annual_summary.empty:
                return None
            if "metric_th" not in annual_summary.columns:
                return None
            for p in patterns:
                hit = annual_summary[
                    annual_summary["metric_th"]
                    .astype(str)
                    .str.contains(p, case=False, na=False, regex=False)
                ]
                if not hit.empty:
                    return hit.iloc[0]
            return None

        def _delta_label(chg, good_up=True, neutral=3.0):
            """สร้าง label ภาษาไทยจาก % change"""
            if chg is None:
                return "—"
            if abs(chg) < neutral:
                return "ทรงตัว"
            if good_up:
                return "เติบโต" if chg > 0 else "ชะลอตัว"
            else:
                return "เพิ่มขึ้น" if chg > 0 else "ลดลง"

        def _delta_dir(chg, good_up=True):
            """สีของ delta: up=เขียว, down=แดง, flat=เทา"""
            if chg is None or abs(chg) < 0.5:
                return "flat"
            if good_up:
                return "up" if chg > 0 else "down"
            else:
                return "down" if chg > 0 else "up"

        # ---------- คำนวณค่าพื้นฐาน ----------
        reg_curr = reg["new_registrations"].iloc[-1]
        reg_prev = reg["new_registrations"].iloc[-2] if len(reg) > 1 else reg_curr
        reg_chg = pct_change(reg_curr, reg_prev)
        reg_cum = reg["cumulative_total"].iloc[-1]

        etc_curr = etc["etc_percent"].iloc[-1]
        etc_prev = etc["etc_percent"].iloc[-2] if len(etc) > 1 else etc_curr
        etc_chg_pp = etc_curr - etc_prev

        topup_curr = topup_total["total_baht"].iloc[-1]
        topup_prev = topup_total["total_baht"].iloc[-2] if len(topup_total) > 1 else topup_curr
        topup_chg = pct_change(topup_curr, topup_prev)

        anom_curr = anomaly["total_events"].iloc[-1]
        anom_prev = anomaly["total_events"].iloc[-2] if len(anomaly) > 1 else anom_curr
        anom_chg = pct_change(anom_curr, anom_prev)

        traf_curr = etc["total_traffic_million"].iloc[-1]
        traf_prev = etc["total_traffic_million"].iloc[-2] if len(etc) > 1 else traf_curr
        traf_chg = pct_change(traf_curr, traf_prev)

        cs_curr = cs["total_cases"].iloc[-1]
        cs_prev = cs["total_cases"].iloc[-2] if len(cs) > 1 else cs_curr
        cs_chg = pct_change(cs_curr, cs_prev)

        # ---------- Health Score & Status ----------
        total_tracked = n_critical + n_warning + n_normal
        health_score = int(round((n_normal / total_tracked * 100) if total_tracked else 100))
        if health_score >= 70:
            h_color, h_icon, h_text = "#2E7D32", "🟢", "ภาพรวมอยู่ในเกณฑ์ดี"
        elif health_score >= 40:
            h_color, h_icon, h_text = "#F57C00", "🟠", "ภาพรวมต้องเฝ้าระวัง"
        else:
            h_color, h_icon, h_text = "#D32F2F", "🔴", "ภาพรวมต้องแก้ไขเร่งด่วน"

        # ====================================================
        # SECTION TITLE
        # ====================================================
        st.markdown(
            section_title(f"📌 บทสรุปผู้บริหาร (Executive Summary) — {LATEST_MONTH}"),
            unsafe_allow_html=True,
        )

        # ====================================================
        # HERO BANNER — Health + Counts
        # ====================================================
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#001233 0%,#003366 55%,#0B5ED7 100%);
                    border-radius:14px;padding:20px 26px;margin-bottom:16px;color:#FFFFFF;
                    box-shadow:0 8px 28px rgba(0,51,102,0.28);
                    display:flex;justify-content:space-between;align-items:center;gap:20px;">
            <div style="flex:1;">
                <div style="font-size:12px;opacity:0.85;letter-spacing:0.5px;margin-bottom:6px;">
                    ภาพรวมระบบ EASY PASS · การทางพิเศษแห่งประเทศไทย
                </div>
                <div style="font-size:22px;font-weight:800;letter-spacing:0.3px;margin-bottom:8px;">
                    {h_icon} {h_text}
                </div>
                <div style="font-size:13px;opacity:0.95;line-height:1.6;">
                    ติดตามทั้งหมด <b>{total_tracked}</b> ตัวชี้วัด
                    &nbsp;·&nbsp; 🔴 วิกฤต <b>{n_critical}</b>
                    &nbsp;·&nbsp; 🟠 เฝ้าระวัง <b>{n_warning}</b>
                    &nbsp;·&nbsp; 🟢 ปกติ <b>{n_normal}</b>
                </div>
            </div>
            <div style="text-align:center;padding:12px 20px;
                        background:rgba(255,255,255,0.12);border-radius:12px;
                        border:1px solid rgba(255,255,255,0.25);">
                <div style="font-size:11px;opacity:0.85;letter-spacing:0.5px;">HEALTH SCORE</div>
                <div style="font-size:38px;font-weight:800;line-height:1;margin:4px 0;">
                    {health_score}
                </div>
                <div style="font-size:11px;opacity:0.85;">จาก 100</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ====================================================
        # HERO KPIs — 4 ตัวเลขสำคัญ
        # ====================================================
        h1, h2, h3, h4 = st.columns(4)

        with h1:
            st.markdown(
                kpi_tile(
                    "👥 ผู้ใช้บัตรสะสมทั้งหมด",
                    f"{reg_cum:,.0f}",
                    f"{reg_chg:+.1f}% MoM · {_delta_label(reg_chg)}",
                    color="blue",
                    delta_dir=_delta_dir(reg_chg, good_up=True),
                ),
                unsafe_allow_html=True,
            )

        with h2:
            st.markdown(
                kpi_tile(
                    "🚗 ปริมาณจราจรเดือนนี้",
                    f"{traf_curr:.2f} ล้านคัน",
                    f"{traf_chg:+.1f}% MoM · {_delta_label(traf_chg, neutral=2)}",
                    color="teal",
                    delta_dir=_delta_dir(traf_chg, good_up=True),
                ),
                unsafe_allow_html=True,
            )

        with h3:
            st.markdown(
                kpi_tile(
                    "📊 สัดส่วน ETC",
                    f"{etc_curr:.2f}%",
                    f"{etc_chg_pp:+.2f} pp MoM",
                    color="purple",
                    delta_dir=_delta_dir(etc_chg_pp, good_up=True),
                ),
                unsafe_allow_html=True,
            )

        with h4:
            st.markdown(
                kpi_tile(
                    "💰 ยอดเติมเงินเดือนนี้",
                    f"{topup_curr/1e6:,.1f} ลบ.",
                    f"{topup_chg:+.1f}% MoM · {_delta_label(topup_chg)}",
                    color="green",
                    delta_dir=_delta_dir(topup_chg, good_up=True),
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        # ====================================================
        # DOMAIN CARDS — 3 มิติ: การเงิน / ปฏิบัติการ / ลูกค้า
        # ====================================================
        def _domain_card(icon, title, metric_name, metric_value, delta_text,
                         status, status_color, status_bg, note=""):
            return f"""
            <div style="background:#FFFFFF;border-radius:12px;padding:16px 18px;
                        border:1px solid #E0E6ED;border-top:4px solid {status_color};
                        box-shadow:0 2px 10px rgba(0,51,102,0.06);height:100%;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;
                            margin-bottom:10px;">
                    <div style="font-size:14px;font-weight:700;color:#003366;">
                        {icon} {title}
                    </div>
                    <span style="background:{status_bg};color:{status_color};
                                 font-size:10.5px;font-weight:700;padding:3px 10px;
                                 border-radius:12px;white-space:nowrap;">{status}</span>
                </div>
                <div style="font-size:12px;color:#5A5A5A;margin-bottom:4px;">{metric_name}</div>
                <div style="font-size:24px;font-weight:700;color:#003366;line-height:1.2;
                            margin-bottom:6px;">{metric_value}</div>
                <div style="font-size:12.5px;font-weight:600;color:{status_color};">{delta_text}</div>
                {f'<div style="font-size:11.5px;color:#777;margin-top:8px;line-height:1.5;">{note}</div>' if note else ''}
            </div>
            """

        def _status_of(chg, good_up=True, warn=3, crit=8):
            if chg is None:
                return "—", "#757575", "#EEEEEE"
            if good_up:
                if chg <= -crit: return "🔴 วิกฤต", "#D32F2F", "#FFEBEE"
                if chg <= -warn: return "🟠 เฝ้าระวัง", "#F57C00", "#FFF8E1"
                return "🟢 ปกติ", "#2E7D32", "#E8F5E9"
            else:
                if chg >= crit: return "🔴 วิกฤต", "#D32F2F", "#FFEBEE"
                if chg >= warn: return "🟠 เฝ้าระวัง", "#F57C00", "#FFF8E1"
                return "🟢 ปกติ", "#2E7D32", "#E8F5E9"

        fin_st, fin_c, fin_bg = _status_of(topup_chg, good_up=True)
        ops_st, ops_c, ops_bg = _status_of(anom_chg, good_up=False, warn=5, crit=15)
        cus_st, cus_c, cus_bg = _status_of(cs_chg, good_up=False, warn=5, crit=15)

        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(_domain_card(
                "💰", "การเงิน", "ยอดเติมเงินสำรองค่าผ่านทาง",
                f"{topup_curr/1e6:,.1f} ล้านบาท",
                f"{topup_chg:+.1f}% MoM",
                fin_st, fin_c, fin_bg,
                note=f"เฉลี่ย {topup_curr/month_days(topup_total)/1e6:,.2f} ลบ./วัน"
            ), unsafe_allow_html=True)

        with d2:
            st.markdown(_domain_card(
                "🚦", "ปฏิบัติการ", "เหตุการณ์ไม้กั้นไม่เปิด",
                f"{anom_curr:,.0f} ครั้ง",
                f"{anom_chg:+.1f}% MoM",
                ops_st, ops_c, ops_bg,
                note=f"เฉลี่ย {anom_curr/month_days(anomaly):,.0f} ครั้ง/วัน"
            ), unsafe_allow_html=True)

        with d3:
            st.markdown(_domain_card(
                "☎️", "ลูกค้า", "เรื่องร้องเรียนศูนย์บริการ",
                f"{cs_curr:,.0f} เรื่อง",
                f"{cs_chg:+.1f}% MoM",
                cus_st, cus_c, cus_bg,
                note=f"สะสมปีงบ {cs['total_cases'].sum():,.0f} เรื่อง"
            ), unsafe_allow_html=True)

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # ====================================================
        # ATTENTION LINE — bridge ไปยัง 🚨 ศูนย์แจ้งเตือน
        # (รายละเอียดเต็มอยู่ในหัวข้อ 🚨 สถานะการเฝ้าระวังภาพรวม ด้านล่าง)
        # ====================================================
        if n_critical > 0:
            _att_icon, _att_color, _att_bg, _att_border = "🔴", "#8B0000", "#FFEBEE", "#D32F2F"
            _att_msg = (
                f"มี <b>{n_critical} รายการ</b> อยู่ในเกณฑ์วิกฤต "
                f"และ <b>{n_warning} รายการ</b> อยู่ในเกณฑ์เฝ้าระวัง"
            )
        elif n_warning > 0:
            _att_icon, _att_color, _att_bg, _att_border = "🟠", "#8B4500", "#FFF8E1", "#F57C00"
            _att_msg = (
                f"มี <b>{n_warning} รายการ</b> อยู่ในเกณฑ์เฝ้าระวัง "
                f"ส่วนที่เหลือ <b>{n_normal} รายการ</b> อยู่ในเกณฑ์ปกติ"
            )
        else:
            _att_icon, _att_color, _att_bg, _att_border = "🟢", "#1B5E20", "#E8F5E9", "#2E7D32"
            _att_msg = (
                f"ตัวชี้วัดทั้ง <b>{total_tracked} รายการ</b> อยู่ในเกณฑ์ปกติทั้งหมด"
            )

        st.markdown(f"""
        <div style="background:{_att_bg};border-left:4px solid {_att_border};
                    border-radius:8px;padding:11px 16px;margin-top:10px;
                    display:flex;justify-content:space-between;align-items:center;gap:16px;">
            <div style="font-size:13px;color:{_att_color};line-height:1.6;">
                {_att_icon} {_att_msg}
            </div>
            <div style="font-size:11.5px;color:{_att_color};font-weight:700;
                        white-space:nowrap;opacity:0.85;">
                ↓ ดูรายละเอียดในศูนย์แจ้งเตือนด้านล่าง
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ====================================================
        # INTERPRETATION — สรุปความหมายเป็นภาษาคน
        # ====================================================
        # นับทิศทางบวกลบของตัวชี้วัดหลัก
        positive = sum([
            reg_chg >= 3,
            traf_chg >= 2,
            etc_chg_pp >= 0.3,
            topup_chg >= 3,
            anom_chg <= -3,
            cs_chg <= -3,
        ])
        negative = sum([
            reg_chg <= -3,
            traf_chg <= -2,
            etc_chg_pp <= -0.3,
            topup_chg <= -3,
            anom_chg >= 3,
            cs_chg >= 3,
        ])

        if positive >= 4 and negative == 0:
            takeaway = "ภาพรวมเดือนนี้ <b>แข็งแกร่ง</b> — ตัวชี้วัดหลักส่วนใหญ่เคลื่อนไหวในทิศทางบวก"
            takeaway_color = "#2E7D32"
            takeaway_bg = "#E8F5E9"
        elif negative >= 3:
            takeaway = "ภาพรวมเดือนนี้ <b>ต้องเฝ้าระวัง</b> — มีหลายตัวชี้วัดที่เคลื่อนไหวในทิศทางที่ต้องติดตาม"
            takeaway_color = "#D32F2F"
            takeaway_bg = "#FFEBEE"
        elif negative >= 1:
            takeaway = "ภาพรวมเดือนนี้ <b>ทรงตัวโดยมีจุดที่ต้องจับตา</b> — ตัวชี้วัดส่วนใหญ่อยู่ในเกณฑ์ปกติ แต่มีบางรายการที่ควรติดตามต่อ"
            takeaway_color = "#E65100"
            takeaway_bg = "#FFF8E1"
        else:
            takeaway = "ภาพรวมเดือนนี้ <b>ทรงตัว</b> — ไม่มีการเปลี่ยนแปลงที่มีนัยสำคัญในตัวชี้วัดหลัก"
            takeaway_color = "#0B5ED7"
            takeaway_bg = "#E3F2FD"

        # ป้อนตัวเลขประกอบ
        key_facts = []
        key_facts.append(
            f"ผู้ใช้บัตรสะสม <b>{reg_cum:,.0f}</b> ราย"
            f" · สมัครใหม่เดือนนี้ <b>{reg_curr:,.0f}</b> ราย"
        )
        key_facts.append(
            f"ปริมาณจราจร <b>{traf_curr:.2f} ล้านคัน</b>"
            f" · ETC <b>{etc_curr:.2f}%</b>"
        )
        key_facts.append(
            f"ยอดเติมเงิน <b>{topup_curr/1e6:,.1f} ล้านบาท</b>"
            f" · ไม้กั้นไม่เปิด <b>{anom_curr:,.0f} ครั้ง</b>"
        )

        # ---- Spacer: แยก Executive Summary ออกจาก section ถัดไป ----
        st.markdown(
            '<div style="height:28px;"></div>'
            '<hr style="border:none;border-top:1px dashed #C7D2E0;margin:0 0 22px 0;">',
            unsafe_allow_html=True,
        )

    else:
        # n_error > 0
        st.markdown(
            '<div class="warning-banner">⚠️ '
            'ไม่สามารถแสดงบทสรุปผู้บริหารได้ เนื่องจากพบปัญหาข้อมูล '
            'กรุณาตรวจสอบที่แท็บ "📥 จัดการข้อมูล CSV"</div>',
            unsafe_allow_html=True,
        )

    # ========================================================
    # KPI CARDS — วิกฤต / เฝ้าระวัง / ปกติ / Health Score
    # ========================================================
    total_alerts = n_critical + n_warning + n_normal
    if total_alerts == 0:
        health_score = 0
        health_icon = "⚪"
        health_label = "ไม่มีข้อมูลเพียงพอ"
    elif total_alerts < 5:
        health_score = int(round(n_normal / total_alerts * 100))
        health_icon = "🟠"
        health_label = "ข้อมูลน้อย — ตีความด้วยความระวัง"
    else:
        health_score = int(round(n_normal / total_alerts * 100))
        health_icon = "🟢" if health_score >= 70 else "🟠" if health_score >= 40 else "🔴"
        health_label = "ระบบสุขภาพดี" if health_score >= 70 else "ต้องเฝ้าระวัง" if health_score >= 40 else "ต้องแก้ไขเร่งด่วน"

    wb1, wb2, wb3, wb4 = st.columns(4)
    wb1.markdown(
        f'<div class="alert-card alert-critical">🔴 วิกฤต<br>'
        f'<span style="font-size:22px;font-weight:700;">{n_critical} รายการ</span></div>',
        unsafe_allow_html=True,
    )
    wb2.markdown(
        f'<div class="alert-card alert-warning">🟠 เฝ้าระวัง<br>'
        f'<span style="font-size:22px;font-weight:700;">{n_warning} รายการ</span></div>',
        unsafe_allow_html=True,
    )
    wb3.markdown(
        f'<div class="alert-card alert-normal">🟢 ปกติ<br>'
        f'<span style="font-size:22px;font-weight:700;">{n_normal} รายการ</span></div>',
        unsafe_allow_html=True,
    )
    wb4.markdown(
        f'<div class="alert-card" style="background:linear-gradient(135deg,#003366,#0B5ED7);">'
        f'{health_icon} ดัชนีสุขภาพระบบ<br>'
        f'<span style="font-size:22px;font-weight:700;">{health_score} / 100</span><br>'
        f'<span style="font-size:11.5px;opacity:0.9;">{health_label}</span></div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # INFO BANNER — ขนาดภาพรวม
    # ========================================================
    if not alerts_df.empty:
        st.markdown(
            f'<div class="info-banner">'
            f'📊 ระบบติดตามทั้งหมด <b>{total_alerts} ตัวชี้วัด</b> — '
            f'มี <b style="color:#D32F2F;">{n_critical} รายการ</b> ที่ต้องแก้ไขเร่งด่วน '
            f'และ <b style="color:#E65100;">{n_warning} รายการ</b> ที่ต้องเฝ้าระวัง'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ========================================================
    # DONUT CHART + PRIORITY ITEMS LIST
    # ========================================================
    if not alerts_df.empty:
        dcol1, dcol2 = st.columns([1, 1.7])

        # ---------- Donut ----------
        with dcol1:
            status_counts = pd.DataFrame(
                {
                    "สถานะ": ["🔴 วิกฤต", "🟠 เฝ้าระวัง", "🟢 ปกติ"],
                    "จำนวน": [n_critical, n_warning, n_normal],
                }
            )
            status_counts = status_counts[status_counts["จำนวน"] > 0]

            if not status_counts.empty:
                fig_status = px.pie(
                    status_counts,
                    names="สถานะ",
                    values="จำนวน",
                    hole=0.6,
                    color="สถานะ",
                    color_discrete_map={
                        "🔴 วิกฤต": "#D32F2F",
                        "🟠 เฝ้าระวัง": "#F57C00",
                        "🟢 ปกติ": "#2E7D32",
                    },
                )
                fig_status.update_traces(
                    textinfo="label+value+percent",
                    textfont_size=11,
                )
                fig_status.update_layout(
                    height=340,
                    showlegend=False,
                    margin=dict(l=5, r=5, t=10, b=10),
                    annotations=[
                        dict(
                            text=f"<b>{total_alerts}</b><br>"
                                 f"<span style='font-size:11px;'>ตัวชี้วัด</span>",
                            x=0.5, y=0.5,
                            font_size=16,
                            showarrow=False,
                        )
                    ],
                )
                st.plotly_chart(fig_status, use_container_width=True)

        # ---------- Priority Items ----------
        with dcol2:
            priority_df = alerts_df[
                alerts_df["สถานะ"].isin(["CRITICAL", "WARNING"])
            ].copy()
            priority_df["_order"] = priority_df["สถานะ"].map(
                {"CRITICAL": 0, "WARNING": 1}
            )
            priority_df = (
                priority_df.sort_values("_order").head(6).reset_index(drop=True)
            )

            if priority_df.empty:
                st.markdown(
                    '<div class="success-banner">'
                    '✅ <b>ทุกตัวชี้วัดอยู่ในระดับปกติ</b> — '
                    'ไม่มีรายการที่ต้องเฝ้าระวังเป็นพิเศษในเดือนนี้'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div style="margin-top:10px;font-size:13px;color:#444;line-height:1.7;">'
                    'ระบบติดตามตัวชี้วัดสำคัญด้านการดำเนินงาน การเงิน '
                    'ลูกค้า และสินค้าคงคลัง เมื่อทุกรายการอยู่ในเกณฑ์ปกติ '
                    'ถือว่าภาพรวมของระบบอยู่ในสถานะที่ดี'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"**🎯 รายการที่ต้องให้ความสำคัญเป็นลำดับแรก** "
                    f"<span style='color:#666;font-weight:400;font-size:12.5px;'>"
                    f"(แสดง {len(priority_df)} จาก {n_critical + n_warning} รายการ)"
                    f"</span>",
                    unsafe_allow_html=True,
                )

                for _, row in priority_df.iterrows():
                    is_crit = row["สถานะ"] == "CRITICAL"
                    icon = "🔴" if is_crit else "🟠"
                    label = "วิกฤต" if is_crit else "เฝ้าระวัง"
                    color = "#D32F2F" if is_crit else "#F57C00"
                    bg = "#FFEBEE" if is_crit else "#FFF8E1"

                    # กลุ่ม A/D ใช้เกณฑ์คงที่ (absolute/ratio) → ไม่มีความหมายของ "เดือนก่อน"
                    # กลุ่ม B/C ใช้ MoM/YoY → แสดง "เดือนก่อน" ตามปกติ
                    grp = row.get("กลุ่ม", "")
                    if grp in ("A", "D"):
                        middle_line = (
                            f'เกณฑ์อ้างอิง: '
                            f'<b style="color:{color};">{row["เปลี่ยนแปลง"]}</b>'
                        )
                    else:
                        middle_line = (
                            f'เดือนก่อน: <b>{row["เดือนก่อน"]}</b>'
                            f' &nbsp;|&nbsp; เปลี่ยนแปลง: '
                            f'<b style="color:{color};">{row["เปลี่ยนแปลง"]}</b>'
                        )

                    st.markdown(
                        f"""
                        <div style="background:{bg};border-left:4px solid {color};
                                    border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                            <div style="display:flex;justify-content:space-between;
                                        align-items:center;gap:10px;">
                                <span style="font-weight:700;color:#003366;font-size:13.5px;">
                                    {icon} {row['หัวข้อ']}
                                </span>
                                <span style="background:{color};color:#FFFFFF;
                                             font-size:10.5px;font-weight:700;
                                             padding:2px 10px;border-radius:10px;
                                             white-space:nowrap;">{label}</span>
                            </div>
                            <div style="font-size:12.5px;color:#555;margin-top:6px;">
                                ค่าล่าสุด: <b style="color:{color};">{row['ค่าล่าสุด']}</b>
                                &nbsp;|&nbsp; {middle_line}
                            </div>
                            <div style="font-size:12px;color:#666;margin-top:5px;
                                        font-style:italic;">
                                📌 {row['คำแนะนำ']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ====================================================
        # สรุปสิ่งที่ต้องจับตา (สำหรับผู้บริหาร)
        # ====================================================
        if n_critical > 0:
            top_crit = alerts_df[alerts_df["สถานะ"] == "CRITICAL"].iloc[0]
            st.markdown(
                f"""
                <div style="background:#FFEBEE;border-radius:8px;
                            padding:12px 16px;margin-top:10px;
                            border-left:4px solid #D32F2F;">
                    <div style="font-size:13px;color:#8B0000;line-height:1.7;">
                        <b>⚡ สรุปสิ่งที่ต้องจับตา:</b>
                        จากทั้งหมด {total_alerts} ตัวชี้วัด มี
                        <b>{n_critical} รายการ</b> ที่อยู่ในเกณฑ์วิกฤต
                        โดยรายการแรกที่ต้องให้ความสำคัญคือ
                        <b>{top_crit['หัวข้อ']}</b>
                        ({top_crit['เปลี่ยนแปลง']})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif n_warning > 0:
            st.markdown(
                f"""
                <div style="background:#FFF8E1;border-radius:8px;
                            padding:12px 16px;margin-top:10px;
                            border-left:4px solid #F57C00;">
                    <div style="font-size:13px;color:#E65100;line-height:1.7;">
                        <b>⚡ สรุปสิ่งที่ต้องจับตา:</b>
                        ไม่มีรายการระดับวิกฤต แต่มี <b>{n_warning} รายการ</b>
                        ที่อยู่ในเกณฑ์เฝ้าระวัง ควรติดตามแนวโน้มต่อเนื่อง
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background:#E8F5E9;border-radius:8px;
                            padding:12px 16px;margin-top:10px;
                            border-left:4px solid #2E7D32;">
                    <div style="font-size:13px;color:#1B5E20;line-height:1.7;">
                        <b>⚡ สรุปสิ่งที่ต้องจับตา:</b>
                        ทุกตัวชี้วัดอยู่ในเกณฑ์ปกติ ไม่มีรายการที่ต้องแก้ไขเร่งด่วน
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(section_title("📊 ตัวชี้วัดหลัก (KPI)"), unsafe_allow_html=True)
    if n_error == 0:
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            st.markdown(kpi_tile("💳 ยอดสมัครสะสมทั้งหมด", f"{reg['cumulative_total'].iloc[-1]:,.0f}",
                                  f"เดือนนี้ {reg['new_registrations'].iloc[-1]:+,.0f}", color="blue", delta_dir="up"), unsafe_allow_html=True)
        with r1c2:
            st.markdown(kpi_tile("🪪 บัตร Active", f"{card_status['active_cards'].iloc[-1]:,.0f}",
                                  f"{card_status['active_cards'].iloc[-1]-card_status['active_cards'].iloc[-2]:+,.0f} บัตร", color="green", delta_dir="up"), unsafe_allow_html=True)
        with r1c3:
            st.markdown(kpi_tile("🚦 สัดส่วน ETC", f"{etc['etc_percent'].iloc[-1]:.2f}%",
                                  f"{etc['etc_percent'].iloc[-1]-etc['etc_percent'].iloc[-2]:+.2f} pp", color="purple", delta_dir="up"), unsafe_allow_html=True)
        with r1c4:
            st.markdown(kpi_tile("💰 ยอดเติมเงินเดือนนี้", f"{topup_total['total_baht'].iloc[-1]/1e6:,.1f} ลบ.",
                                  f"{pct_change(topup_total['total_baht'].iloc[-1], topup_total['total_baht'].iloc[-2]):+.1f}%", color="orange", delta_dir="up"), unsafe_allow_html=True)
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            st.markdown(kpi_tile("🚗 ปริมาณจราจรรวม", f"{etc['total_traffic_million'].iloc[-1]:.2f} ล้านคัน",
                                  f"{pct_change(etc['total_traffic_million'].iloc[-1], etc['total_traffic_million'].iloc[-2]):+.1f}%", color="teal", delta_dir="up"), unsafe_allow_html=True)
        with r2c2:
            st.markdown(kpi_tile("⚠️ เหตุการณ์ไม้กั้น", f"{anomaly['total_events'].iloc[-1]:,.0f}",
                                  f"{pct_change(anomaly['total_events'].iloc[-1], anomaly['total_events'].iloc[-2]):+.1f}%", color="red", delta_dir="down"), unsafe_allow_html=True)
        with r2c3:
            st.markdown(kpi_tile("🆘 บัตรสูญหาย", f"{card_status['lost_count'].iloc[-1]:,.0f}",
                                  f"{card_status['lost_count'].iloc[-1]-card_status['lost_count'].iloc[-2]:+,.0f} บัตร", color="red", delta_dir="down"), unsafe_allow_html=True)
        with r2c4:
            st.markdown(kpi_tile("☎️ เรื่องร้องเรียน CS", f"{cs['total_cases'].iloc[-1]:,.0f}",
                                  f"{cs['total_cases'].iloc[-1]-cs['total_cases'].iloc[-2]:+,.0f} เรื่อง", color="orange", delta_dir="down"), unsafe_allow_html=True)

    st.markdown(section_title("📈 แนวโน้มหลัก 4 ด้าน"), unsafe_allow_html=True)
    if n_error == 0:
        tcol1, tcol2 = st.columns(2)
        with tcol1:
            fig1 = go.Figure()
            fig1.add_bar(x=reg["month_label"], y=reg["new_registrations"], name="สมัครใหม่", marker_color="#0B5ED7")
            fig1.add_trace(go.Scatter(x=reg["month_label"], y=reg["cumulative_total"], name="สะสม", yaxis="y2",
                                       line=dict(color="#F57C00", width=2.5)))
            fig1.update_layout(title="📈 ยอดสมัครใช้บัตร Easy Pass", height=320,
                               yaxis=dict(title="สมัครใหม่"), yaxis2=dict(title="สะสม", overlaying="y", side="right"),
                               legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig1, use_container_width=True)
        with tcol2:
            fig2 = px.line(etc, x="month_label", y="etc_percent", markers=True, title="🚦 สัดส่วน ETC (%)")
            fig2.update_traces(line_color="#6A1B9A", line_width=3, marker=dict(size=8))
            fig2.update_layout(height=320, showlegend=False, plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig2, use_container_width=True)
        tcol3, tcol4 = st.columns(2)
        with tcol3:
            fig3 = px.area(topup_total, x="month_label", y="total_baht", title="💰 ยอดเติมเงิน (บาท)")
            fig3.update_traces(line_color="#2E7D32")
            fig3.update_layout(height=320, showlegend=False, plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig3, use_container_width=True)
        with tcol4:
            fig4 = px.area(anomaly, x="month_label", y="total_events", title="⚠️ เหตุการณ์ไม้กั้นไม่เปิด")
            fig4.update_traces(line_color="#D32F2F")
            fig4.update_layout(height=320, showlegend=False, plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig4, use_container_width=True)

    if n_error == 0 and not traffic_full.empty and not card_detail.empty:
        st.markdown(section_title("🏆 Performance Deep-Dive"), unsafe_allow_html=True)
        left, right = st.columns([1.2, 1])

        # ====================================================
        # LEFT — Top 5 สายทาง
        #
        # ปรับปรุง:
        #   - label บนแท่งระบุหน่วยชัดเจน "เที่ยว" และ "Easy Pass"
        #   - ไม่ต้องอาศัย caption อธิบายความหมายของวงเล็บ
        #   - จัดวาง 2 บรรทัดบนแท่งให้อ่านง่าย (ค่าหลัก / ค่ารอง)
        # ====================================================
        with left:
            st.markdown("**🛣️ Top 5 สายทางที่มีปริมาณจราจรสูงสุด**")
            traf_routes = traffic_full[
                ~traffic_full["route_code"].astype(str).str.contains("รวม", na=False)
            ].copy()
            traf_routes = traf_routes.sort_values("total_traffic", ascending=False).head(5)

            if not traf_routes.empty:
                # label 2 บรรทัด: บรรทัดบน = ปริมาณ+หน่วย, บรรทัดล่าง = % Easy Pass
                traf_routes["label_text"] = traf_routes.apply(
                    lambda r: (
                        f"{r['total_traffic']:,.0f} เที่ยว"
                        f"<br>"
                        f"<span style='font-size:10px;'>"
                        f"Easy Pass {r['percent_easypass']:.1f}%"
                        f"</span>"
                    ),
                    axis=1,
                )

                fig_top = px.bar(
                    traf_routes,
                    x="total_traffic",
                    y="route_name",
                    orientation="h",
                    text="label_text",
                    custom_data=["percent_easypass"],
                )
                fig_top.update_traces(
                    marker_color="#0B5ED7",
                    marker_line_color="#003366",
                    marker_line_width=1,
                    texttemplate="%{text}",
                    textposition="outside",
                    textfont=dict(size=11, color="#003366"),
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "ปริมาณจราจร: %{x:,.0f} เที่ยว<br>"
                        "Easy Pass: %{customdata[0]:.2f}%<br>"
                        "<extra></extra>"
                    ),
                )
                fig_top.update_layout(
                    height=360,
                    showlegend=False,
                    yaxis=dict(
                        autorange="reversed",
                        title="",
                        tickfont=dict(size=11),
                    ),
                    xaxis=dict(
                        title="ปริมาณจราจร (เที่ยว)",
                        gridcolor="#E0E6ED",
                    ),
                    margin=dict(l=10, r=140, t=10, b=40),
                    plot_bgcolor="#FAFBFC",
                    bargap=0.4,
                )
                st.plotly_chart(fig_top, use_container_width=True)

        # ====================================================
        # RIGHT — Pie สถานะบัตร
        #
        # ปรับปรุง:
        #   - จัดกลุ่มด้วย status_group ก่อน
        #   - แจกเฉดสีต่างกันภายในกลุ่มเดียวกัน (ไม่ใช้ keyword matching)
        #   - สีหลักยังสื่อความหมาย: เขียว=พร้อมใช้, ส้ม=ไม่พร้อม, แดง=หาย
        #   - รับประกันว่าแต่ละ status_name ได้สีไม่ซ้ำกันจริง
        # ====================================================
        with right:
            st.markdown("**💳 สถานะบัตร Easy Pass**")
            card_show = card_detail[
                card_detail["status_group"].isin(
                    ["บัตรพร้อมใช้งาน", "บัตรไม่พร้อมใช้งาน", "บัตรหาย"]
                )
            ].copy()
            card_show = card_show[
                ~card_show["status_name"].str.contains("รวม", na=False)
            ]

            if not card_show.empty:
                # เฉดสีตามกลุ่ม — เรียงจากเข้มไปอ่อน
                GROUP_SHADES = {
                    "บัตรพร้อมใช้งาน": [
                        "#1B5E20", "#2E7D32", "#43A047", "#66BB6A", "#81C784",
                    ],
                    "บัตรไม่พร้อมใช้งาน": [
                        "#BF360C", "#E65100", "#F57C00", "#FB8C00", "#FFB74D",
                    ],
                    "บัตรหาย": [
                        "#7F0000", "#B71C1C", "#D32F2F", "#E53935", "#EF5350",
                    ],
                }
                FALLBACK_PALETTE = [
                    "#0B5ED7", "#6A1B9A", "#00838F", "#5D4037", "#C2185B",
                ]

                color_map_name = {}
                for grp, grp_df in card_show.groupby("status_group"):
                    names = list(grp_df["status_name"].unique())
                    palette = GROUP_SHADES.get(grp, FALLBACK_PALETTE)
                    for i, nm in enumerate(names):
                        color_map_name[nm] = palette[i % len(palette)]

                fig_card = px.pie(
                    card_show,
                    names="status_name",
                    values="total_count",
                    color="status_name",
                    color_discrete_map=color_map_name,
                    hole=0.5,
                )
                fig_card.update_traces(
                    textinfo="label+percent",
                    textfont_size=10,
                    marker=dict(line=dict(color="#FFFFFF", width=2)),
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "จำนวน: %{value:,.0f} ใบ<br>"
                        "สัดส่วน: %{percent}<br>"
                        "<extra></extra>"
                    ),
                )
                fig_card.update_layout(
                    height=360,
                    legend=dict(
                        orientation="h",
                        y=-0.18,
                        font=dict(size=9),
                    ),
                    margin=dict(l=5, r=5, t=10, b=10),
                )
                st.plotly_chart(fig_card, use_container_width=True)

    if n_error == 0:
        st.markdown(
            section_title("🔍 Supporting Metrics — ข้อมูลสนับสนุนการตัดสินใจ"),
            unsafe_allow_html=True,
        )

        # ---------- Helper: safe extract ----------
        def _safe(df, col, idx=-1, default=None):
            try:
                if df is None or df.empty or col not in df.columns:
                    return default
                return df[col].iloc[idx]
            except Exception:
                return default

        # ---------- 1) Easy Pass vs M-Pass ----------
        ep_share = mp_share = None
        if not mpass_detail.empty:
            try:
                exat_row = mpass_detail[mpass_detail["route_code"] == "รวม กทพ."]
                doh_row = mpass_detail[mpass_detail["route_code"] == "รวม ทล."]
                ep_sum = mp_sum = 0
                if not exat_row.empty:
                    ep_sum += float(exat_row["easypass_transactions"].iloc[0])
                    mp_sum += float(exat_row["mpass_transactions"].iloc[0])
                if not doh_row.empty:
                    ep_sum += float(doh_row["easypass_transactions"].iloc[0])
                    mp_sum += float(doh_row["mpass_transactions"].iloc[0])
                total_epmp = ep_sum + mp_sum
                if total_epmp > 0:
                    ep_share = ep_sum / total_epmp * 100
                    mp_share = mp_sum / total_epmp * 100
            except Exception:
                pass

        # ---------- 2,3) สายทางสูงสุด/ต่ำสุด % EP ----------
        top_route_name = low_route_name = None
        top_route_pct = low_route_pct = None
        if not route.empty:
            try:
                ROUTE_COLS = {
                    "chalerm_mahanakorn": "เฉลิมมหานคร",
                    "srirat": "ศรีรัช",
                    "chalong_rat": "ฉลองรัช",
                    "burapha_withi": "บูรพาวิถี",
                    "kanchanaphisek": "กาญจนาภิเษก",
                    "udornratthaya": "อุดรรัถยา",
                    "srirat_outer_ring": "ประจิมรัถยา",
                }
                latest_route = {
                    label: float(route[col].iloc[-1])
                    for col, label in ROUTE_COLS.items()
                    if col in route.columns
                }
                if latest_route:
                    sorted_r = sorted(latest_route.items(), key=lambda x: x[1], reverse=True)
                    top_route_name, top_route_pct = sorted_r[0]
                    low_route_name, low_route_pct = sorted_r[-1]
            except Exception:
                pass

        # ---------- 4) บัตรไม่เคลื่อนไหว ----------
        inactive_cards = inactive_amount = None
        if not inactive_bal.empty:
            try:
                tot_row = inactive_bal[
                    inactive_bal["amount_range"].astype(str).str.contains("รวม", na=False)
                ]
                if not tot_row.empty:
                    inactive_cards = float(tot_row["card_count"].iloc[0])
                    inactive_amount = float(tot_row["amount_baht"].iloc[0])
            except Exception:
                pass

        # ---------- 5) อัตราบัตรหาย ----------
        lost_rate = None
        try:
            lost_c = float(card_status["lost_count"].iloc[-1])
            active_c = float(card_status["active_cards"].iloc[-1])
            if active_c > 0:
                lost_rate = lost_c / active_c * 100
        except Exception:
            pass

        # ---------- 6) หน่วยงานภายนอก Top 1 ----------
        top_agency_name = top_agency_share = None
        if not topup_ext.empty:
            try:
                top_ag = topup_ext.sort_values("share_percent", ascending=False).iloc[0]
                top_agency_name = str(top_ag["agency"])
                top_agency_share = float(top_ag["share_percent"])
            except Exception:
                pass

        # ---------- Build tiles ----------
        tiles = []

        if ep_share is not None and mp_share is not None:
            tiles.append({
                "icon": "🅿️",
                "label": "Easy Pass vs M-Pass",
                "value": f"{ep_share:.1f}% / {mp_share:.1f}%",
                "sub": "สัดส่วนธุรกรรม 2 ระบบ (กทพ.+ทล.)",
                "color": "blue",
            })

        if top_route_name is not None:
            tiles.append({
                "icon": "🏆",
                "label": "สายทาง % Easy Pass สูงสุด",
                "value": f"{top_route_pct:.1f}%",
                "sub": top_route_name,
                "color": "green",
            })

        if low_route_name is not None:
            tiles.append({
                "icon": "⚠️",
                "label": "สายทาง % Easy Pass ต่ำสุด",
                "value": f"{low_route_pct:.1f}%",
                "sub": low_route_name,
                "color": "orange",
            })

        if lost_rate is not None:
            tiles.append({
                "icon": "🆘",
                "label": "อัตราบัตรหาย",
                "value": f"{lost_rate:.2f}%",
                "sub": "เทียบกับบัตร Active",
                "color": "red",
            })

        if inactive_cards is not None and inactive_amount is not None:
            tiles.append({
                "icon": "💤",
                "label": "บัตรไม่เคลื่อนไหว >2 ปี",
                "value": f"{inactive_cards:,.0f} ใบ",
                "sub": f"มูลค่า {inactive_amount/1e6:,.1f} ลบ.",
                "color": "purple",
            })

        if top_agency_name is not None:
            tiles.append({
                "icon": "🏢",
                "label": "หน่วยงานเติมเงิน Top 1",
                "value": f"{top_agency_share:.1f}%",
                "sub": top_agency_name[:30],
                "color": "teal",
            })

        # ---------- Render ----------
        if tiles:
            n_cols = min(len(tiles), 3)
            n_rows = (len(tiles) + n_cols - 1) // n_cols

            BORDER_COLOR = {
                "blue": "#0B5ED7", "green": "#2E7D32", "orange": "#F57C00",
                "red": "#D32F2F", "purple": "#6A1B9A", "teal": "#00838F",
            }

            for r in range(n_rows):
                cols = st.columns(n_cols)
                for c in range(n_cols):
                    idx = r * n_cols + c
                    if idx >= len(tiles):
                        break
                    t = tiles[idx]
                    border = BORDER_COLOR.get(t["color"], "#0B5ED7")
                    with cols[c]:
                        st.markdown(f"""
                        <div style="background:#FFFFFF;border-radius:10px;
                                    padding:14px 16px;border:1px solid #E0E6ED;
                                    border-left:5px solid {border};
                                    box-shadow:0 2px 8px rgba(0,51,102,0.06);
                                    height:100%;">
                            <div style="font-size:11.5px;color:#777;font-weight:600;
                                        margin-bottom:6px;">{t['icon']} {t['label']}</div>
                            <div style="font-size:22px;font-weight:700;color:#003366;
                                        line-height:1.1;margin-bottom:4px;">{t['value']}</div>
                            <div style="font-size:11.5px;color:#666;">{t['sub']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        else:
            st.caption("ℹ️ ยังไม่มีข้อมูลเพียงพอสำหรับแสดง Supporting Metrics")


        st.markdown(section_title("💡 Interpretation — ภาพรวมข้อมูล"), unsafe_allow_html=True)
        overview_bullets = [
            f"ยอดสมัครใหม่เดือนล่าสุด {reg_curr:,.0f} บัตร เปลี่ยนแปลง {reg_chg:+.1f}% จากเดือนก่อน ขณะที่ยอดสะสมอยู่ที่ {reg['cumulative_total'].iloc[-1]:,.0f} บัตร",
            f"ปริมาณจราจรรวม {traf_curr:.2f} ล้านคัน เปลี่ยนแปลง {pct_change(traf_curr, etc['total_traffic_million'].iloc[-2]):+.1f}% และสัดส่วน ETC อยู่ที่ {etc_curr:.2f}%",
            f"ยอดเติมเงินรวม {topup_curr/1e6:,.1f} ล้านบาท เปลี่ยนแปลง {topup_chg:+.1f}% จากเดือนก่อน",
            f"เหตุการณ์ไม้กั้นไม่เปิด {anom_curr:,.0f} ครั้ง เปลี่ยนแปลง {anom_chg:+.1f}% จากเดือนก่อน",
            f"เรื่องร้องเรียนศูนย์บริการ {cs_curr:,.0f} เรื่อง เปลี่ยนแปลง {cs_chg:+.1f}% จากเดือนก่อน",
            "ภาพรวมควรอ่านเป็นชุดตัวชี้วัดที่เคลื่อนไหวร่วมกัน มากกว่าตัดสินจาก KPI ใด KPI หนึ่ง เพราะแต่ละชุดมีหน่วย ฐานประชากร และความหมายต่างกัน"
        ]
        st.markdown(html_interpretation("ภาพรวม Executive Dashboard", overview_bullets,
            "เป็น descriptive interpretation ของข้อมูลรายเดือน ไม่ใช่ข้อสรุปเชิงสาเหตุหรือข้อเสนอเชิงนโยบาย"), unsafe_allow_html=True)

# =============================================================================
# TAB: 🪪 ยอดสมัคร & คงคลังบัตร
# =============================================================================
if tab_card is not None:
    with tab_card:
        st.markdown(section_title(f"📋 1. ยอดสมัครใช้บัตร Easy Pass — {LATEST_MONTH}", "หน้า 2"), unsafe_allow_html=True)
        if n_error == 0 and not reg.empty:
            latest_new = reg["new_registrations"].iloc[-1]
            cum_total = reg["cumulative_total"].iloc[-1]
            reg_chg = pct_change(latest_new, reg["new_registrations"].iloc[-2])
            avg_daily = latest_new / month_days(reg)
            fy69_reg = annual_summary[annual_summary["metric_th"].str.contains("บัตรใหม่สะสม", na=False)]
            fy69_val = fy69_reg["value"].iloc[0] if not fy69_reg.empty else latest_new

            kc1, kc2, kc3, kc4 = st.columns(4)
            with kc1:
                st.markdown(kpi_tile("📅 สมัครใหม่เดือนนี้", f"{latest_new:,.0f}", f"{reg_chg:+.1f}% MoM", color="blue", delta_dir="up" if reg_chg >= 0 else "down"), unsafe_allow_html=True)
            with kc2:
                st.markdown(kpi_tile("📊 สะสมทั้งหมด", f"{cum_total:,.0f}", "ตั้งแต่เริ่มระบบ", color="green"), unsafe_allow_html=True)
            with kc3:
                st.markdown(kpi_tile("📈 สะสมปีงบ 69", f"{fy69_val:,.0f}", f"ข้อมูลสะสมถึง {LATEST_MONTH}", color="purple"), unsafe_allow_html=True)
            with kc4:
                st.markdown(kpi_tile("📊 เฉลี่ย/วัน", f"{avg_daily:,.0f}", "บัตร/วัน", color="teal"), unsafe_allow_html=True)
            st.markdown("---")

            col_a, col_b = st.columns([1.4, 1])
            with col_a:
                fig = go.Figure()
                fig.add_bar(x=reg["month_label"], y=reg["new_registrations"], name="สมัครใหม่", marker_color="#0B5ED7")
                fig.add_trace(go.Scatter(x=reg["month_label"], y=reg["cumulative_total"], name="สะสม", yaxis="y2",
                                          line=dict(color="#F57C00", width=3)))
                fig.update_layout(title="ยอดสมัครรายเดือน + สะสม", height=430,
                                   yaxis=dict(title="สมัครใหม่"), yaxis2=dict(title="สะสม", overlaying="y", side="right"),
                                   legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                rd = reg.copy()
                rd["new_registrations"] = rd["new_registrations"].apply(lambda x: f"{x:,.0f}")
                rd["cumulative_total"] = rd["cumulative_total"].apply(lambda x: f"{x:,.0f}")
                rd = rd[["month_label", "new_registrations", "cumulative_total"]]
                rd.columns = ["เดือน", "สมัครใหม่", "สะสม"]
                st.dataframe(rd, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        if not reg_by_route.empty:
            st.markdown(sub_section_title(f"🛣️ 1.1 ยอดจำหน่ายบัตร แยกตามสายทาง (ข้อมูลสะสมถึง {LATEST_MONTH})", "หน้า 2"), unsafe_allow_html=True)

            def _fmt(x):
                try:
                    if pd.isna(x): return "-"
                    v = float(x)
                    return "0" if v == 0 else f"{int(v):,}"
                except: return "-"

            col_r1, col_r2 = st.columns([1.3, 1])
            with col_r1:
                rrd = reg_by_route.copy()
                for c in ["monthly_aug69", "fy69_cumulative", "since_start"]:
                    rrd[c] = rrd[c].apply(_fmt)
                rrd = rrd[["route_code", "route_name", "monthly_aug69", "fy69_cumulative", "since_start"]]
                rrd.columns = ["รหัส", "สายทาง", LATEST_MONTH, "ปีงบ 69 สะสม", "ตั้งแต่เริ่ม"]
                st.dataframe(rrd, use_container_width=True, hide_index=True, height=440)
            with col_r2:
                rrc = reg_by_route[reg_by_route["route_code"] != "รวม"].copy()
                if not rrc.empty:
                    fig_rr = px.bar(rrc, x="monthly_aug69", y="route_name", orientation="h",
                                    text="monthly_aug69", title=f"ยอดสมัครบัตร {LATEST_MONTH}",
                                    color="monthly_aug69", color_continuous_scale="Blues")
                    fig_rr.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_rr.update_layout(height=440, showlegend=False, coloraxis_showscale=False,
                                         yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_rr, use_container_width=True)
            st.markdown("---")

        st.markdown(section_title("📦 2. ยอดคงเหลือบัตร Easy Pass ทั้งหมด", "หน้า 3"), unsafe_allow_html=True)
        if n_error == 0 and not inv.empty:
            obu_now = inv["obu_stock"].iloc[-1]; sc_now = inv["smartcard_stock"].iloc[-1]
            obu_prev = inv["obu_stock"].iloc[-2]; sc_prev = inv["smartcard_stock"].iloc[-2]
            obu_status = status_from_abs(obu_now, th_obu_warn, th_obu_crit)
            sc_status = status_from_abs(sc_now, th_sc_warn, th_sc_crit)
            obu_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "NORMAL": "🟢"}[obu_status]
            sc_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "NORMAL": "🟢"}[sc_status]

            ic1, ic2, ic3, ic4 = st.columns(4)
            with ic1:
                st.markdown(kpi_tile(f"{obu_icon} OBU คงเหลือ", f"{obu_now:,.0f}", f"{pct_change(obu_now, obu_prev):+.1f}% MoM", color="blue", delta_dir="down"), unsafe_allow_html=True)
            with ic2:
                st.markdown(kpi_tile(f"{sc_icon} Smart Card คงเหลือ", f"{sc_now:,.0f}", f"{pct_change(sc_now, sc_prev):+.1f}% MoM", color="purple", delta_dir="down"), unsafe_allow_html=True)
            with ic3:
                st.markdown(kpi_tile("📦 รวมคงคลัง", f"{obu_now+sc_now:,.0f}", "OBU + Smart Card", color="teal"), unsafe_allow_html=True)
            with ic4:
                first_total = inv["obu_stock"].iloc[0] + inv["smartcard_stock"].iloc[0]
                usage_pct = (first_total - (obu_now+sc_now)) / first_total * 100 if first_total > 0 else 0
                st.markdown(kpi_tile("📉 อัตราการใช้สต็อก", f"{usage_pct:.1f}%", f"ใช้ไป {first_total-(obu_now+sc_now):,.0f} ใบ", color="orange"), unsafe_allow_html=True)
            st.markdown("---")

            pc1, pc2 = st.columns(2)
            with pc1:
                obu_max = th_obu_warn * 1.5
                obu_pct_bar = min(obu_now / obu_max * 100, 100)
                obu_color = "#D32F2F" if obu_status == "CRITICAL" else "#F57C00" if obu_status == "WARNING" else "#2E7D32"
                st.markdown(f'<div style="padding:14px 18px;background:#F8FAFC;border-radius:10px;">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                            f'<b>🔷 OBU (ใบ)</b><span style="color:{obu_color};font-weight:700;">{obu_now:,.0f} ใบ ({obu_icon})</span></div>'
                            f'<div style="background:#E0E6ED;border-radius:20px;height:14px;overflow:hidden;">'
                            f'<div style="width:{obu_pct_bar}%;background:{obu_color};height:100%;border-radius:20px;"></div></div>'
                            f'<div style="display:flex;justify-content:space-between;font-size:11.5px;color:#666;margin-top:6px;">'
                            f'<span>วิกฤต: {th_obu_crit:,.0f}</span><span>เตือน: {th_obu_warn:,.0f}</span></div></div>', unsafe_allow_html=True)
            with pc2:
                sc_max = th_sc_warn * 1.5
                sc_pct_bar = min(sc_now / sc_max * 100, 100)
                sc_color = "#D32F2F" if sc_status == "CRITICAL" else "#F57C00" if sc_status == "WARNING" else "#2E7D32"
                st.markdown(f'<div style="padding:14px 18px;background:#F8FAFC;border-radius:10px;">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                            f'<b>🟣 Smart Card (ใบ)</b><span style="color:{sc_color};font-weight:700;">{sc_now:,.0f} ใบ ({sc_icon})</span></div>'
                            f'<div style="background:#E0E6ED;border-radius:20px;height:14px;overflow:hidden;">'
                            f'<div style="width:{sc_pct_bar}%;background:{sc_color};height:100%;border-radius:20px;"></div></div>'
                            f'<div style="display:flex;justify-content:space-between;font-size:11.5px;color:#666;margin-top:6px;">'
                            f'<span>วิกฤต: {th_sc_crit:,.0f}</span><span>เตือน: {th_sc_warn:,.0f}</span></div></div>', unsafe_allow_html=True)
            st.markdown("---")

            fig_inv_trend = go.Figure()
            fig_inv_trend.add_trace(go.Scatter(x=inv["month_label"], y=inv["obu_stock"], mode="lines+markers",
                                                name="OBU", line=dict(color="#0B5ED7", width=3)))
            fig_inv_trend.add_trace(go.Scatter(x=inv["month_label"], y=inv["smartcard_stock"], mode="lines+markers",
                                                name="Smart Card", line=dict(color="#6A1B9A", width=3)))
            fig_inv_trend.add_hline(y=th_obu_warn, line_dash="dash", line_color="orange")
            fig_inv_trend.add_hline(y=th_obu_crit, line_dash="dash", line_color="red")
            fig_inv_trend.add_hline(y=th_sc_warn, line_dash="dot", line_color="purple")
            fig_inv_trend.add_hline(y=th_sc_crit, line_dash="dot", line_color="#8B0000")
            fig_inv_trend.update_layout(title="แนวโน้มยอดคงเหลือบัตร", height=430,
                                         legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig_inv_trend, use_container_width=True)
            st.markdown("---")

        if not inv_by_route.empty:
            st.markdown(sub_section_title(f"🛣️ 2.1 ยอดคงเหลือ ณ {LATEST_MONTH} แยกสายทาง", "หน้า 3"), unsafe_allow_html=True)
            col_i1, col_i2 = st.columns([1.3, 1])
            with col_i1:
                ird = inv_by_route.copy()
                ird["obu_stock"] = ird["obu_stock"].apply(lambda x: f"{x:,.0f}")
                ird["smartcard_stock"] = ird["smartcard_stock"].apply(lambda x: f"{x:,.0f}")
                ird["รวม"] = (inv_by_route["obu_stock"] + inv_by_route["smartcard_stock"]).apply(lambda x: f"{x:,.0f}")
                ird = ird[["route_name", "obu_stock", "smartcard_stock", "รวม"]]
                ird.columns = ["สายทาง / คลัง", "OBU", "Smart Card", "รวม"]
                st.dataframe(ird, use_container_width=True, hide_index=True, height=440)
            with col_i2:
                intra = inv_by_route[inv_by_route["route_name"] != "รวมทั้งหมด"].copy()
                if not intra.empty:
                    fig_inv_bar = go.Figure()
                    fig_inv_bar.add_bar(x=intra["route_name"], y=intra["obu_stock"], name="OBU", marker_color="#0B5ED7")
                    fig_inv_bar.add_bar(x=intra["route_name"], y=intra["smartcard_stock"], name="Smart Card", marker_color="#6A1B9A")
                    fig_inv_bar.update_layout(title="ยอดคงเหลือแยกสายทาง", barmode="group", height=440,
                                               xaxis_tickangle=-30, legend=dict(orientation="h", y=1.12))
                    st.plotly_chart(fig_inv_bar, use_container_width=True)
            st.markdown("---")

        if n_error == 0 and not inv.empty:
            st.markdown(sub_section_title("📋 3. ตารางแนวโน้มรายเดือน"), unsafe_allow_html=True)
            inv_disp = inv.copy()
            inv_disp["obu_fmt"] = inv_disp["obu_stock"].apply(lambda x: f"{x:,.0f}")
            inv_disp["sc_fmt"] = inv_disp["smartcard_stock"].apply(lambda x: f"{x:,.0f}")
            inv_disp["total_fmt"] = (inv["obu_stock"] + inv["smartcard_stock"]).apply(lambda x: f"{x:,.0f}")
            inv_disp["obu_chg"] = inv["obu_stock"].diff().fillna(0).apply(lambda x: f"{x:+,.0f}" if x != 0 else "-")
            inv_disp["sc_chg"] = inv["smartcard_stock"].diff().fillna(0).apply(lambda x: f"{x:+,.0f}" if x != 0 else "-")
            inv_disp = inv_disp[["month_label", "obu_fmt", "obu_chg", "sc_fmt", "sc_chg", "total_fmt"]]
            inv_disp.columns = ["เดือน", "OBU", "Δ OBU", "Smart Card", "Δ SC", "รวม"]
            st.dataframe(inv_disp, use_container_width=True, hide_index=True)

        if n_error == 0 and not reg.empty and not inv.empty:
            st.markdown(sub_section_title("💡 4. Card Analytics"), unsafe_allow_html=True)
            n_months = len(inv)
            obu_start = inv["obu_stock"].iloc[0]; sc_start = inv["smartcard_stock"].iloc[0]
            obu_now_f = inv["obu_stock"].iloc[-1]; sc_now_f = inv["smartcard_stock"].iloc[-1]
            obu_burn = (obu_start - obu_now_f) / (n_months - 1) if n_months > 1 else 0
            sc_burn = (sc_start - sc_now_f) / (n_months - 1) if n_months > 1 else 0
            months_left_obu = obu_now_f / obu_burn if obu_burn > 0 else 999
            months_left_sc = sc_now_f / sc_burn if sc_burn > 0 else 999

            def fmt_duration(m):
                if m >= 999: return "∞"
                y = int(m // 12); mo = int(m % 12)
                if y > 0 and mo > 0: return f"{y} ปี {mo} เดือน"
                if y > 0: return f"{y} ปี"
                return f"{mo} เดือน"

            def months_to_thr(current, threshold, burn):
                if burn <= 0 or current <= threshold: return 0
                return (current - threshold) / burn

            obu_to_crit = months_to_thr(obu_now_f, th_obu_crit, obu_burn)
            sc_to_crit = months_to_thr(sc_now_f, th_sc_crit, sc_burn)

            try:
                curr_m = str(inv["month"].iloc[-1]).strip().split("-")
                cy, cm = int(curr_m[0]), int(curr_m[1])
            except: cy, cm = 2026, 8

            _TH = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
            def fcast(m):
                try:
                    t = cy * 12 + (cm - 1) + int(m); ny = t // 12; nm = (t % 12) + 1
                    return f"{_TH[nm-1]} {str(ny+543)[-2:]}"
                except: return "-"

            obu_state = status_from_abs(obu_now_f, th_obu_warn, th_obu_crit)
            sc_state = status_from_abs(sc_now_f, th_sc_warn, th_sc_crit)
            obu_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "NORMAL": "🟢"}[obu_state]
            sc_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "NORMAL": "🟢"}[sc_state]
            obu_label = {"CRITICAL": "วิกฤต", "WARNING": "เฝ้าระวัง", "NORMAL": "เพียงพอ"}[obu_state]
            sc_label = {"CRITICAL": "วิกฤต", "WARNING": "เฝ้าระวัง", "NORMAL": "เพียงพอ"}[sc_state]

            st.markdown("**📊 ข้อมูลอ้างอิง**")
            st.dataframe(pd.DataFrame({
                "รายการ": ["สต็อกเริ่มต้น", "สต็อกปัจจุบัน", "อัตราการใช้ (ใบ/เดือน)",
                           "ใช้ได้อีก", "คาดแตะวิกฤต"],
                "🔷 OBU": [f"{obu_start:,.0f}", f"{obu_now_f:,.0f}", f"{obu_burn:,.0f}",
                           fmt_duration(months_left_obu), f"อีก {obu_to_crit:.1f} เดือน ({fcast(obu_to_crit)})"],
                "🟣 Smart Card": [f"{sc_start:,.0f}", f"{sc_now_f:,.0f}", f"{sc_burn:,.0f}",
                                  fmt_duration(months_left_sc), f"อีก {sc_to_crit:.1f} เดือน ({fcast(sc_to_crit)})"],
            }), use_container_width=True, hide_index=True)
            st.markdown("---")

            ins_col1, ins_col2 = st.columns(2)
            obu_bc = "#FFEBEE" if obu_state == "CRITICAL" else "#FFF8E1" if obu_state == "WARNING" else "#E8F5E9"
            obu_bord = "#D32F2F" if obu_state == "CRITICAL" else "#F57C00" if obu_state == "WARNING" else "#2E7D32"
            sc_bc = "#FFEBEE" if sc_state == "CRITICAL" else "#FFF8E1" if sc_state == "WARNING" else "#E8F5E9"
            sc_bord = "#D32F2F" if sc_state == "CRITICAL" else "#F57C00" if sc_state == "WARNING" else "#2E7D32"

            with ins_col1:
                st.markdown(f'<div style="background:{obu_bc};border-radius:10px;padding:16px 18px;border-left:5px solid {obu_bord};">'
                            f'<h4 style="margin:0 0 10px 0;color:#003366;">🔷 คลัง OBU</h4>'
                            f'<div style="font-size:22px;font-weight:700;color:{obu_bord};">{obu_icon} {obu_label}</div>'
                            f'<div style="font-size:13px;color:#444;line-height:1.7;margin-top:8px;">'
                            f'คงเหลือ <b>{obu_now_f:,.0f}</b> ใบ • ใช้ <b>{obu_burn:,.0f}</b> ใบ/เดือน<br>'
                            f'ใช้ได้อีก <b>{fmt_duration(months_left_obu)}</b></div></div>', unsafe_allow_html=True)
            with ins_col2:
                st.markdown(f'<div style="background:{sc_bc};border-radius:10px;padding:16px 18px;border-left:5px solid {sc_bord};">'
                            f'<h4 style="margin:0 0 10px 0;color:#003366;">🟣 คลัง Smart Card</h4>'
                            f'<div style="font-size:22px;font-weight:700;color:{sc_bord};">{sc_icon} {sc_label}</div>'
                            f'<div style="font-size:13px;color:#444;line-height:1.7;margin-top:8px;">'
                            f'คงเหลือ <b>{sc_now_f:,.0f}</b> ใบ • ใช้ <b>{sc_burn:,.0f}</b> ใบ/เดือน<br>'
                            f'ใช้ได้อีก <b>{fmt_duration(months_left_sc)}</b></div></div>', unsafe_allow_html=True)

            obu_need = max(0, obu_burn * 12 + th_obu_warn - obu_now_f)
            sc_need = max(0, sc_burn * 12 + th_sc_warn - sc_now_f)
            st.markdown(build_stock_interpretation(
                obu_state, sc_state, obu_burn, sc_burn, obu_to_crit, sc_to_crit,
                obu_now_f, sc_now_f, th_obu_warn, th_obu_crit, th_sc_warn, th_sc_crit
            ), unsafe_allow_html=True)

# =============================================================================
# TAB: 🚦 ปริมาณจราจร & ETC
# =============================================================================
if tab_traffic is not None:
    with tab_traffic:
        st.markdown(section_title(f"📊 3.1 ปริมาณจราจรรถทั้งหมด vs ETC เฉพาะเดือน {LATEST_MONTH}", "หน้า 5"), unsafe_allow_html=True)
        st.markdown("""<div class="info-banner">
            📖 ETC = Easy Pass + EMV (ใช้ได้เฉพาะรถ 4 ล้อ) • ข้อมูลจากระบบรายงานปริมาณจราจร/รายได้
        </div>""", unsafe_allow_html=True)

        if n_error == 0 and not etc.empty:
            traf_now = etc["total_traffic_million"].iloc[-1]; traf_prev = etc["total_traffic_million"].iloc[-2]
            etc_now = etc["etc_traffic_million"].iloc[-1]; etc_prev = etc["etc_traffic_million"].iloc[-2]
            pct_now = etc["etc_percent"].iloc[-1]; pct_prev = etc["etc_percent"].iloc[-2]
            avg_daily = etc["avg_daily_etc"].iloc[-1]

            if not traffic_4w.empty:
                tw_now = traffic_4w["traffic_4wheel_million"].iloc[-1]
                tw_prev = traffic_4w["traffic_4wheel_million"].iloc[-2]
                etc_tw = traffic_4w["etc_4wheel_million"].iloc[-1]
                etc_tw_prev = traffic_4w["etc_4wheel_million"].iloc[-2]
                etc_tw_pct = traffic_4w["etc_4wheel_percent"].iloc[-1]
                etc_tw_pct_delta = etc_tw_pct - traffic_4w["etc_4wheel_percent"].iloc[-2]
            else: tw_now = tw_prev = etc_tw = etc_tw_prev = etc_tw_pct = etc_tw_pct_delta = 0

            if not emv.empty:
                emv_now = emv["emv_traffic_million"].iloc[-1]
                emv_pct = emv["emv_percent"].iloc[-1]
                emv_pct_delta = emv_pct - emv["emv_percent"].iloc[-2]
            else: emv_now = emv_pct = emv_pct_delta = 0

            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            with r1c1:
                st.markdown(kpi_tile("🚗 ปริมาณจราจรรถทั้งหมด", f"{traf_now:.2f} ล้านคัน", f"{pct_change(traf_now, traf_prev):+.1f}% MoM", color="teal"), unsafe_allow_html=True)
            with r1c2:
                st.markdown(kpi_tile("🛣️ ETC รวม", f"{etc_now:.2f} ล้านคัน", f"{pct_change(etc_now, etc_prev):+.1f}% MoM", color="blue"), unsafe_allow_html=True)
            with r1c3:
                st.markdown(kpi_tile("📊 สัดส่วน ETC", f"{pct_now:.2f}%", f"{pct_now-pct_prev:+.2f} pp MoM", color="purple"), unsafe_allow_html=True)
            with r1c4:
                st.markdown(kpi_tile("📈 เฉลี่ย ETC/วัน", f"{avg_daily:,.0f}", "คัน/วัน", color="green"), unsafe_allow_html=True)
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            with r2c1:
                st.markdown(kpi_tile("🚙 รถ 4 ล้อ", f"{tw_now:.2f} ล้านคัน", f"{pct_change(tw_now, tw_prev):+.1f}% MoM", color="orange"), unsafe_allow_html=True)
            with r2c2:
                st.markdown(kpi_tile("🅿️ Easy Pass", f"{etc_tw:.2f} ล้านคัน", f"{pct_change(etc_tw, etc_tw_prev):+.1f}% MoM", color="brown"), unsafe_allow_html=True)
            with r2c3:
                st.markdown(kpi_tile("📊 EP / 4 ล้อ", f"{etc_tw_pct:.2f}%", f"{etc_tw_pct_delta:+.2f} pp", color="pink"), unsafe_allow_html=True)
            with r2c4:
                st.markdown(kpi_tile("💳 EMV", f"{emv_now:.2f} ล้านคัน", f"{emv_pct:.2f}% ({emv_pct_delta:+.2f} pp)", color="purple"), unsafe_allow_html=True)
            st.markdown("---")

        st.markdown(sub_section_title("📈 3.1 ปริมาณจราจรรวม vs ETC รายเดือน", "หน้า 5"), unsafe_allow_html=True)
        if n_error == 0 and not etc.empty:
            col_e1, col_e2 = st.columns([1.4, 1])
            with col_e1:
                fig_etc = go.Figure()
                fig_etc.add_bar(x=etc["month_label"], y=etc["total_traffic_million"], name="จราจรรวม", marker_color="#B0BEC5")
                fig_etc.add_bar(x=etc["month_label"], y=etc["etc_traffic_million"], name="ETC รวม", marker_color="#0B5ED7")
                fig_etc.add_trace(go.Scatter(x=etc["month_label"], y=etc["etc_percent"], name="% ETC", yaxis="y2",
                                              line=dict(color="#F57C00", width=3)))
                fig_etc.update_layout(barmode="group", title="จราจรรวม vs ETC", height=430,
                                       yaxis=dict(title="ล้านคัน"), yaxis2=dict(title="ร้อยละ", overlaying="y", side="right"),
                                       legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_etc, use_container_width=True)
            with col_e2:
                ed = etc.copy()
                for c, f in [("total_traffic_million", "{:.2f}"), ("etc_traffic_million", "{:.2f}"), ("etc_percent", "{:.2f}%"), ("avg_daily_etc", "{:,.0f}")]:
                    ed[c] = ed[c].apply(lambda x, fm=f: fm.format(x))
                ed = ed[["month_label", "total_traffic_million", "etc_traffic_million", "etc_percent", "avg_daily_etc"]]
                ed.columns = ["เดือน", "รวม", "ETC", "% ETC", "เฉลี่ย/วัน"]
                st.dataframe(ed, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        st.markdown(sub_section_title(f"📊 3.2 ปริมาณจราจร ETC สะสมปีงบประมาณ 2569 (ข้อมูลสะสมถึง {LATEST_MONTH})", "หน้า 5"), unsafe_allow_html=True)
        if n_error == 0 and not etc.empty:
            etc_cum = etc.copy()
            etc_cum["cum_total_million"] = etc_cum["total_traffic_million"].cumsum()
            etc_cum["cum_etc_million"] = etc_cum["etc_traffic_million"].cumsum()
            etc_cum["cum_etc_percent"] = (etc_cum["cum_etc_million"] / etc_cum["cum_total_million"] * 100).round(2)
            etc_cum["cum_avg_daily_etc"] = (etc_cum["cum_etc_million"] * 1e6 / (etc_cum["month"].apply(lambda m: month_days(pd.DataFrame({"month":[m]}))).cumsum())).round(0)

            tot_all = etc_cum["total_traffic_million"].sum()
            tot_etc = etc_cum["etc_traffic_million"].sum()
            tot_pct = safe_pct(tot_etc, tot_all)
            tot_days = sum(month_days(pd.DataFrame({"month":[m]})) for m in etc_cum["month"]); tot_avg_daily = tot_etc * 1e6 / tot_days if tot_days else 0

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.markdown(kpi_tile("📊 จราจรรวมสะสม", f"{tot_all:.2f} ล้านคัน", f"ข้อมูลสะสมถึง {LATEST_MONTH}", color="teal"), unsafe_allow_html=True)
            with sc2:
                st.markdown(kpi_tile("🛣️ ETC สะสม", f"{tot_etc:.2f} ล้านคัน", "Easy Pass + EMV", color="blue"), unsafe_allow_html=True)
            with sc3:
                st.markdown(kpi_tile("📈 สัดส่วน ETC สะสม", f"{tot_pct:.2f}%", "เฉลี่ยทั้งปีงบ", color="purple"), unsafe_allow_html=True)
            with sc4:
                st.markdown(kpi_tile("📅 เฉลี่ย ETC/วัน", f"{tot_avg_daily:,.0f}", "คัน/วัน", color="green"), unsafe_allow_html=True)
            st.markdown("---")

            col_c1, col_c2 = st.columns([1.4, 1])
            with col_c1:
                fig_cum = go.Figure()
                fig_cum.add_bar(x=etc_cum["month_label"], y=etc_cum["cum_total_million"],
                                name="จราจรรวมสะสม", marker_color="#B0BEC5")
                fig_cum.add_bar(x=etc_cum["month_label"], y=etc_cum["cum_etc_million"],
                                name="ETC สะสม", marker_color="#0B5ED7")
                fig_cum.add_trace(go.Scatter(x=etc_cum["month_label"], y=etc_cum["cum_etc_percent"],
                                              name="% ETC สะสม", yaxis="y2",
                                              line=dict(color="#F57C00", width=3), marker=dict(size=8)))
                fig_cum.update_layout(barmode="group", title="ETC สะสมปีงบ 2569",
                                       height=430, yaxis=dict(title="ล้านคัน (สะสม)"),
                                       yaxis2=dict(title="ร้อยละ (%)", overlaying="y", side="right"),
                                       legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_cum, use_container_width=True)
            with col_c2:
                cd = etc_cum.copy()
                cd["cum_total_million"] = cd["cum_total_million"].apply(lambda x: f"{x:.2f}")
                cd["cum_etc_million"] = cd["cum_etc_million"].apply(lambda x: f"{x:.2f}")
                cd["cum_etc_percent"] = cd["cum_etc_percent"].apply(lambda x: f"{x:.2f}%")
                cd["cum_avg_daily_etc"] = cd["cum_avg_daily_etc"].apply(lambda x: f"{x:,.0f}")
                cd = cd[["month_label", "cum_total_million", "cum_etc_million", "cum_etc_percent", "cum_avg_daily_etc"]]
                cd.columns = ["เดือน", "รวมสะสม", "ETC สะสม", "% สะสม", "เฉลี่ย/วัน"]
                st.dataframe(cd, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        st.markdown(sub_section_title("🛣️ 3.2b ร้อยละ ETC แยกตามสายทาง (สถิติย้อนหลังรายเดือน)", "หน้า 6"), unsafe_allow_html=True)
        if n_error == 0 and not route.empty:
            rcm = {"chalerm_mahanakorn": "เฉลิมมหานคร", "srirat": "ศรีรัช", "chalong_rat": "ฉลองรัช",
                   "burapha_withi": "บูรพาวิถี", "kanchanaphisek": "กาญจนาภิเษก",
                   "udornratthaya": "อุดรรัถยา", "srirat_outer_ring": "ประจิมรัถยา"}
            rr = route.rename(columns=rcm)
            lv = {c: rr[c].iloc[-1] for c in rcm.values()}
            sl = sorted(lv.items(), key=lambda x: x[1], reverse=True)
            hn, hv = sl[0]; ln, lv_ = sl[-1]
            avg_all = sum(lv.values()) / len(lv)
            gap = hv - lv_

            kc1, kc2, kc3, kc4 = st.columns(4)
            with kc1: st.markdown(kpi_tile("🏆 สูงสุด", f"{hv:.2f}%", hn, color="green"), unsafe_allow_html=True)
            with kc2: st.markdown(kpi_tile("⚠️ ต่ำสุด", f"{lv_:.2f}%", ln, color="red"), unsafe_allow_html=True)
            with kc3: st.markdown(kpi_tile("📊 เฉลี่ย 7 สาย", f"{avg_all:.2f}%", "เดือนล่าสุด", color="blue"), unsafe_allow_html=True)
            with kc4: st.markdown(kpi_tile("📏 ช่องว่าง", f"{gap:.2f} pp", "สูง-ต่ำ", color="orange"), unsafe_allow_html=True)
            st.markdown(f'<div class="warning-banner">⚠️ <b>{ln}</b> ต่ำสุด <b>{lv_:.2f}%</b> vs <b>{hn}</b> สูงสุด {hv:.2f}%</div>', unsafe_allow_html=True)
            st.markdown("---")

            col_rt1, col_rt2 = st.columns([1.4, 1])
            with col_rt1:
                fig_route = go.Figure()
                colors_route = ["#0B5ED7", "#F57C00", "#2E7D32", "#D32F2F", "#B71C1C", "#00838F", "#5D4037"]
                for i, (ce, ct) in enumerate(rcm.items()):
                    is_low = (ct == ln)
                    fig_route.add_trace(go.Scatter(x=rr["month_label"], y=rr[ct], mode="lines+markers",
                                                    name=f"⚠️ {ct}" if is_low else ct,
                                                    line=dict(color=colors_route[i], width=4 if is_low else 2.5,
                                                              dash="dash" if is_low else "solid"),
                                                    marker=dict(size=10 if is_low else 7)))
                fig_route.update_layout(title="ร้อยละ ETC แยกสายทาง", height=430,
                                         legend=dict(orientation="h", y=-0.15), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_route, use_container_width=True)
            with col_rt2:
                rdd = rr.copy()
                for c in rcm.values(): rdd[c] = rdd[c].apply(lambda x: f"{x:.2f}")
                rdd = rdd[["month_label"] + list(rcm.values())]
                rdd.columns = ["เดือน"] + [c[:12] for c in rcm.values()]
                st.dataframe(rdd, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        st.markdown(sub_section_title(f"🚙 3.3 รถ 4 ล้อ vs Easy Pass เฉพาะเดือน {LATEST_MONTH}", "หน้า 6"), unsafe_allow_html=True)
        if n_error == 0 and not traffic_4w.empty:
            col_4w1, col_4w2 = st.columns([1.4, 1])
            with col_4w1:
                fig_4w = go.Figure()
                fig_4w.add_bar(x=traffic_4w["month_label"], y=traffic_4w["traffic_4wheel_million"], name="4 ล้อทั้งหมด", marker_color="#B0BEC5")
                fig_4w.add_bar(x=traffic_4w["month_label"], y=traffic_4w["etc_4wheel_million"], name="Easy Pass", marker_color="#F57C00")
                fig_4w.add_trace(go.Scatter(x=traffic_4w["month_label"], y=traffic_4w["etc_4wheel_percent"], name="% EP",
                                              yaxis="y2", line=dict(color="#D32F2F", width=3)))
                fig_4w.update_layout(barmode="group", height=430, yaxis=dict(title="ล้านคัน"),
                                      yaxis2=dict(title="ร้อยละ", overlaying="y", side="right"),
                                      legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_4w, use_container_width=True)
            with col_4w2:
                twd = traffic_4w.copy()
                for c, f in [("traffic_4wheel_million", "{:.2f}"), ("etc_4wheel_million", "{:.2f}"), ("etc_4wheel_percent", "{:.2f}%")]:
                    twd[c] = twd[c].apply(lambda x, fm=f: fm.format(x))
                twd = twd[["month_label", "traffic_4wheel_million", "etc_4wheel_million", "etc_4wheel_percent"]]
                twd.columns = ["เดือน", "4 ล้อ", "Easy Pass", "% EP"]
                st.dataframe(twd, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        st.markdown(sub_section_title(f"💳 3.5 ปริมาณ EMV เฉพาะเดือน {LATEST_MONTH}", "หน้า 8"), unsafe_allow_html=True)
        if n_error == 0 and not emv.empty:
            col_emv1, col_emv2 = st.columns([1.4, 1])
            with col_emv1:
                fig_emv = go.Figure()
                fig_emv.add_trace(go.Bar(x=emv["month_label"], y=emv["emv_traffic_million"], name="EMV", marker_color="#6A1B9A"))
                fig_emv.add_trace(go.Scatter(x=emv["month_label"], y=emv["emv_percent"], name="% EMV", yaxis="y2",
                                              line=dict(color="#F57C00", width=3)))
                fig_emv.update_layout(height=430, yaxis=dict(title="ล้านคัน"),
                                       yaxis2=dict(title="ร้อยละ", overlaying="y", side="right"),
                                       legend=dict(orientation="h", y=1.12), plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_emv, use_container_width=True)
            with col_emv2:
                emvd = emv.copy()
                emvd["total_traffic_million"] = emvd["total_traffic_million"].apply(lambda x: f"{x:.2f}")
                emvd["emv_traffic_million"] = emvd["emv_traffic_million"].apply(lambda x: f"{x:.2f}")
                emvd["emv_percent"] = emvd["emv_percent"].apply(lambda x: f"{x:.2f}%")
                emvd = emvd[["month_label", "total_traffic_million", "emv_traffic_million", "emv_percent"]]
                emvd.columns = ["เดือน", "จราจรรวม", "EMV", "% EMV"]
                st.dataframe(emvd, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

# =============================================================================

            st.markdown(sub_section_title("💡 Interpretation — ปริมาณจราจร & ETC"), unsafe_allow_html=True)
            bullets = []
            bullets.append(f"เดือนล่าสุดมีปริมาณจราจรรวม {traf_now:.2f} ล้านคัน และ ETC {etc_now:.2f} ล้านคัน คิดเป็น {pct_now:.2f}% ของจราจรรวม")
            bullets.append(f"สัดส่วน ETC เปลี่ยนจาก {pct_prev:.2f}% เป็น {pct_now:.2f}% ({pct_now-pct_prev:+.2f} pp) ซึ่งสะท้อนการเปลี่ยนแปลงของสัดส่วนการใช้ ETC ในเดือนล่าสุด")
            if not traffic_4w.empty:
                bullets.append(f"ในกลุ่มรถ 4 ล้อ Easy Pass อยู่ที่ {etc_tw_pct:.2f}% ของรถ 4 ล้อทั้งหมด ขณะที่ปริมาณรถ 4 ล้ออยู่ที่ {tw_now:.2f} ล้านคัน")
            if not emv.empty:
                bullets.append(f"EMV มีปริมาณ {emv_now:.2f} ล้านคัน หรือ {emv_pct:.2f}% ของจราจรตามฐานข้อมูล EMV")
            if not route.empty:
                route_latest = {c: route[c].iloc[-1] for c in rcm.keys()}
                top_r = max(route_latest, key=route_latest.get)
                low_r = min(route_latest, key=route_latest.get)
                bullets.append(f"เมื่อมองรายสายทาง ความแตกต่างของสัดส่วน ETC ยังมีอยู่ โดยสายทางสูงสุดคือ {rcm[top_r]} {route_latest[top_r]:.2f}% และต่ำสุดคือ {rcm[low_r]} {route_latest[low_r]:.2f}%")
            st.markdown(html_interpretation("ปริมาณจราจร & ETC", bullets,
                "การเพิ่ม/ลดของ ETC ไม่ควรตีความว่าเกิดจากพฤติกรรมผู้ใช้เพียงอย่างเดียว เพราะปริมาณจราจรรวมเป็นตัวหารของสัดส่วน"), unsafe_allow_html=True)

# TAB: ⚠️ ไม้กั้นไม่เปิด
# =============================================================================
if tab_anomaly is not None:
    with tab_anomaly:
        st.markdown(section_title(f"⚠️ 3.4 สถิติเหตุการณ์ไม้กั้นไม่เปิด (Easy Pass) เดือน {LATEST_MONTH}", "หน้า 7"), unsafe_allow_html=True)
        st.markdown("""<div class="info-banner">
            📖 <b>ไม้กั้นไม่เปิด</b> = เหตุการณ์ที่ระบบ Easy Pass ไม่สามารถอ่านข้อมูลจากบัตรได้ ทำให้ไม้กั้นไม่เปิดโดยอัตโนมัติ<br>
            🟡 ปัญหาระบบ (54%) • 🔵 ปัญหาลูกค้า (46%) • ข้อมูลจากระบบรายงานปริมาณจราจร/รายได้
        </div>""", unsafe_allow_html=True)

        if n_error == 0 and not anomaly.empty and not anomaly_cause.empty:
            anom_now = anomaly["total_events"].iloc[-1]; anom_prev = anomaly["total_events"].iloc[-2]
            anom_chg = pct_change(anom_now, anom_prev)
            sys_total = anomaly_cause[anomaly_cause["category"] == "ระบบ"]["count"].sum()
            cus_total = anomaly_cause[anomaly_cause["category"] == "ลูกค้า"]["count"].sum()
            sys_pct = anomaly_cause[anomaly_cause["category"] == "ระบบ"]["percentage"].sum()
            cus_pct = anomaly_cause[anomaly_cause["category"] == "ลูกค้า"]["percentage"].sum()
            top_cause = anomaly_cause.sort_values("count", ascending=False).iloc[0]
            top_route = anomaly_by_route.sort_values("total_events", ascending=False).iloc[0] if not anomaly_by_route.empty else None

            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            with r1c1:
                st.markdown(kpi_tile("⚠️ เหตุการณ์เดือนนี้", f"{anom_now:,.0f}", f"{anom_chg:+.1f}% MoM", color="red",
                                      delta_dir="down" if anom_chg >= 0 else "up"), unsafe_allow_html=True)
            with r1c2:
                st.markdown(kpi_tile("📈 เฉลี่ย/วัน", f"{anom_now/month_days(anomaly):,.0f}", "ครั้ง/วัน", color="orange"), unsafe_allow_html=True)
            with r1c3:
                st.markdown(kpi_tile("🟡 ปัญหาระบบ", f"{sys_total:,.0f}", f"{sys_pct:.1f}%", color="orange"), unsafe_allow_html=True)
            with r1c4:
                st.markdown(kpi_tile("🔵 ปัญหาลูกค้า", f"{cus_total:,.0f}", f"{cus_pct:.1f}%", color="blue"), unsafe_allow_html=True)
            st.markdown("---")

        if n_error == 0 and not anomaly.empty:
            st.markdown(sub_section_title("📈 แนวโน้มรายเดือน"), unsafe_allow_html=True)
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=anomaly["month_label"], y=anomaly["total_events"], mode="lines+markers",
                                            line=dict(color="#D32F2F", width=3), fill="tozeroy", fillcolor="rgba(211,47,47,0.1)"))
            fig_trend.update_layout(height=430, yaxis=dict(title="ครั้ง"), plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig_trend, use_container_width=True)
            st.markdown("---")

        if n_error == 0 and not anomaly_cause.empty:
            st.markdown(sub_section_title("🥧 สัดส่วนตามประเภทปัญหา"), unsafe_allow_html=True)
            color_map = {"ติดตั้งผิดตำแหน่ง/ไม่ติดตั้ง": "#FFC107", "ไม่พบข้อมูลทางเข้า": "#FFE082",
                         "แบตฯ อ่อน": "#F9A825", "เงินไม่พอ": "#64B5F6", "ไม่มีบัตร": "#2196F3",
                         "ยอดเงินไม่เป็นปัจจุบัน": "#1976D2", "บัตร Blacklist": "#0D47A1"}
            fig_pie = px.pie(anomaly_cause, names="cause_name", values="count",
                              title=f"รวม {anomaly_cause['count'].sum():,.0f} ครั้ง",
                              color="cause_name", color_discrete_map=color_map, hole=0.4)
            fig_pie.update_traces(textinfo="label+percent", textposition="outside", textfont_size=11)
            fig_pie.update_layout(height=480, margin=dict(l=10, r=10, t=80, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown("---")

        if n_error == 0 and not anomaly_by_route.empty:
            st.markdown(sub_section_title("🛣️ เหตุการณ์แยกตามสายทาง"), unsafe_allow_html=True)
            abr = anomaly_by_route.sort_values("total_events", ascending=False).copy()
            fig_route_total = px.bar(abr, x="route_name", y="total_events", text="total_events",
                                      color="total_events", color_continuous_scale="Reds")
            fig_route_total.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_route_total.update_layout(height=430, showlegend=False, coloraxis_showscale=False,
                                           xaxis_tickangle=-20, yaxis_title="ครั้ง", plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig_route_total, use_container_width=True)
            st.markdown("---")

            st.markdown(sub_section_title("📋 ตารางรายละเอียดเหตุการณ์แยกตามสายทางและประเภทปัญหา"), unsafe_allow_html=True)
            abr_tbl = anomaly_by_route.copy()
            abr_tbl.columns = ["สายทาง"] + [c.replace("cause_", "").replace("_", " ") for c in abr_tbl.columns[1:]]
            st.dataframe(abr_tbl, use_container_width=True, hide_index=True)
            st.markdown("---")

        if n_error == 0 and not anomaly.empty and not anomaly_cause.empty and not anomaly_by_route.empty:
            st.markdown(sub_section_title("💡 Interpretation — สิ่งที่ข้อมูลสะท้อน"), unsafe_allow_html=True)
            anom_mom = pct_change(anomaly["total_events"].iloc[-1], anomaly["total_events"].iloc[-2]) if len(anomaly) > 1 else None
            sys_pct = anomaly_cause[anomaly_cause["category"] == "ระบบ"]["percentage"].sum()
            cus_pct = anomaly_cause[anomaly_cause["category"] == "ลูกค้า"]["percentage"].sum()
            top_route = anomaly_by_route.sort_values("total_events", ascending=False).iloc[0]
            top_cause = anomaly_cause.sort_values("count", ascending=False).iloc[0]
            route_share = safe_pct(top_route["total_events"], anomaly_by_route["total_events"].sum())
            cause_share = safe_pct(top_cause["count"], anomaly_cause["count"].sum())
            trend_word = "เพิ่มขึ้น" if (anom_mom or 0) > 0.5 else "ลดลง" if (anom_mom or 0) < -0.5 else "ทรงตัว"
            bullets = [
                f"เดือนล่าสุดมีเหตุการณ์ <b>{anomaly['total_events'].iloc[-1]:,.0f} ครั้ง</b> และ {trend_word} {abs(anom_mom):.1f}% จากเดือนก่อน" if anom_mom is not None else f"เดือนล่าสุดมีเหตุการณ์ <b>{anomaly['total_events'].iloc[-1]:,.0f} ครั้ง</b>",
                f"สัดส่วนเหตุการณ์ตามข้อมูลจำแนกเป็น <b>ปัญหาระบบ {sys_pct:.1f}%</b> และ <b>ปัญหาลูกค้า {cus_pct:.1f}%</b> จึงเห็นได้ว่าปัญหาไม่ได้อยู่ในมิติเดียว",
                f"สาเหตุที่พบมากที่สุดคือ <b>{top_cause['cause_name']}</b> จำนวน {top_cause['count']:,.0f} ครั้ง คิดเป็น {cause_share:.1f}% ของเหตุการณ์ที่จำแนกสาเหตุ",
                f"สายทางที่มีจำนวนเหตุการณ์สูงสุดคือ <b>{top_route['route_name']}</b> จำนวน {top_route['total_events']:,.0f} ครั้ง หรือ {route_share:.1f}% ของเหตุการณ์รวมตามสายทาง",
                "การตีความจากจำนวนเหตุการณ์ควรอ่านควบคู่กับปริมาณจราจรของแต่ละสายทาง เพราะจำนวนเหตุการณ์สูงอาจสะท้อนทั้งปริมาณรถที่สูงและอัตราปัญหาที่สูง ข้อมูลชุดนี้เพียงอย่างเดียวยังสรุปอัตราความเสี่ยงต่อเที่ยวผ่านไม่ได้"
            ]
            st.markdown(html_interpretation("ไม้กั้นไม่เปิด", bullets,
                "Interpretation นี้เป็นการอธิบายสิ่งที่ข้อมูลแสดง ไม่ได้สรุปสาเหตุเชิงเหตุผลหรือเสนอแผนนโยบาย"), unsafe_allow_html=True)


# =============================================================================
# TAB: 🚗 ธุรกรรม Easy Pass/M-Pass
# =============================================================================
if tab_route_merged is not None:
    with tab_route_merged:

        st.markdown(section_title(
            "🚗 ธุรกรรม Easy Pass / M-Pass ตามสายทาง",
            "หน้า 9-12", "กทพ. + กรมทางหลวง + ดอนเมืองโทลล์เวย์"
        ), unsafe_allow_html=True)

        st.markdown("""
        <div class="method-banner">
            🎯 <b>ขอบเขตของแท็บนี้:</b> แสดงธุรกรรม Easy Pass vs M-Pass ใน 3 ระบบ<br>
            &nbsp;&nbsp;&nbsp;&nbsp;• <b>กทพ. 7 สายทาง</b> — Easy Pass vs M-Pass (Comparable)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;• <b>กรมทางหลวง M6/M7/M81</b> — Easy Pass vs M-Pass (Comparable)<br>
            &nbsp;&nbsp;&nbsp;&nbsp;• <b>ดอนเมืองโทลล์เวย์</b> — Easy Pass vs Total (⚠️ ไม่มี M-Pass จึงแยกเปรียบเทียบ)
        </div>
        """, unsafe_allow_html=True)

        if n_error == 0 and not mpass_detail.empty and not tollway_detail.empty:
            # -- กทพ. --
            exat_routes = mpass_detail[mpass_detail["group"] == "กทพ."].copy()
            exat_routes = exat_routes[~exat_routes["route_code"].astype(str).str.contains("รวม", na=False)]
            exat_total_row = mpass_detail[mpass_detail["route_code"] == "รวม กทพ."]

            if not exat_total_row.empty:
                exat_total = exat_total_row["total_transactions"].iloc[0]
                exat_mpass = exat_total_row["mpass_transactions"].iloc[0]
                exat_easypass = exat_total_row["easypass_transactions"].iloc[0]
                exat_mpass_pct = exat_total_row["mpass_percent"].iloc[0]
                exat_easypass_pct = exat_total_row["easypass_percent"].iloc[0]
                exat_avg_daily = exat_total_row["avg_daily"].iloc[0]
            else:
                exat_total = exat_routes["total_transactions"].sum()
                exat_mpass = exat_routes["mpass_transactions"].sum()
                exat_easypass = exat_routes["easypass_transactions"].sum()
                exat_mpass_pct = safe_pct(exat_mpass, exat_total)
                exat_easypass_pct = safe_pct(exat_easypass, exat_total)
                exat_avg_daily = exat_total / month_days(mpass_detail)

            # -- กรมทางหลวง --
            doh_routes = mpass_detail[mpass_detail["group"] == "กรมทางหลวง"].copy()
            doh_routes = doh_routes[~doh_routes["route_code"].astype(str).str.contains("รวม", na=False)]
            doh_total_row = mpass_detail[mpass_detail["route_code"] == "รวม ทล."]

            if not doh_total_row.empty:
                doh_total = doh_total_row["total_transactions"].iloc[0]
                doh_easypass = doh_total_row["easypass_transactions"].iloc[0]
                doh_mpass = doh_total_row["mpass_transactions"].iloc[0]
                doh_easypass_pct = doh_total_row["easypass_percent"].iloc[0]
                doh_mpass_pct = doh_total_row["mpass_percent"].iloc[0]
                doh_avg_daily = doh_total_row["avg_daily"].iloc[0]
            else:
                doh_total = doh_routes["total_transactions"].sum()
                doh_easypass = doh_routes["easypass_transactions"].sum()
                doh_mpass = doh_routes["mpass_transactions"].sum()
                doh_easypass_pct = safe_pct(doh_easypass, doh_total)
                doh_mpass_pct = safe_pct(doh_mpass, doh_total)
                doh_avg_daily = doh_total / month_days(mpass_detail)

            # -- ดอนเมืองโทลล์เวย์ --
            has_easypass_tw = ("easypass_tollway_transactions" in tollway_detail.columns
                               and "easypass_percent" in tollway_detail.columns)
            if has_easypass_tw:
                toll_easypass = tollway_detail["easypass_tollway_transactions"].iloc[-1]
                toll_total_tw = tollway_detail["total_tollway_transactions"].iloc[-1]
                toll_pct = tollway_detail["easypass_percent"].iloc[-1]
                toll_non_ep = toll_total_tw - toll_easypass
            else:
                toll_easypass = toll_total_tw = toll_pct = toll_non_ep = 0

            # -- ภาพรวม 3 ระบบ --
            grand_total = exat_total + doh_total + toll_total_tw
            grand_easypass = exat_easypass + doh_easypass + toll_easypass
            grand_mpass = exat_mpass + doh_mpass

            # ===== KPI Cards: 3 ระบบ =====
            st.markdown(sub_section_title("📊 ภาพรวม 3 ระบบ (Total Overview)"), unsafe_allow_html=True)
            ov1, ov2, ov3, ov4 = st.columns(4)
            with ov1:
                st.markdown(kpi_tile("📊 รวมทั้ง 3 ระบบ", f"{grand_total:,.0f}", "เที่ยว (เดือนนี้)", color="teal"), unsafe_allow_html=True)
            with ov2:
                st.markdown(kpi_tile("🔵 Easy Pass รวม", f"{grand_easypass:,.0f}",
                                      f"{safe_pct(grand_easypass, grand_total):.2f}% ของทั้งหมด", color="blue"), unsafe_allow_html=True)
            with ov3:
                st.markdown(kpi_tile("🟠 M-Pass รวม (กทพ.+ทล.)", f"{grand_mpass:,.0f}",
                                      f"{safe_pct(grand_mpass, exat_total+doh_total):.2f}% ของ กทพ.+ทล.", color="orange"), unsafe_allow_html=True)
            with ov4:
                st.markdown(kpi_tile("🏙️ สัดส่วน ดอนเมืองโทลล์เวย์", f"{safe_pct(toll_total_tw, grand_total):.2f}%",
                                      f"{toll_total_tw:,.0f} เที่ยว", color="purple"), unsafe_allow_html=True)

            col_ov1, col_ov2 = st.columns([1, 1.4])
            with col_ov1:
                pie_ov = pd.DataFrame({
                    "ระบบ": ["กทพ. (7 สายทาง)", "กรมทางหลวง (M6/M7/M81)", "ดอนเมืองโทลล์เวย์"],
                    "ปริมาณ": [exat_total, doh_total, toll_total_tw]
                })
                fig_ov = px.pie(pie_ov, names="ระบบ", values="ปริมาณ",
                                 title="สัดส่วนปริมาณธุรกรรม 3 ระบบ",
                                 color="ระบบ",
                                 color_discrete_map={
                                     "กทพ. (7 สายทาง)": "#0B5ED7",
                                     "กรมทางหลวง (M6/M7/M81)": "#F57C00",
                                     "ดอนเมืองโทลล์เวย์": "#6A1B9A"
                                 },
                                 hole=0.5)
                fig_ov.update_traces(textinfo="label+percent+value",
                                      texttemplate="%{label}<br>%{percent}<br>(%{value:,.0f})",
                                      textfont_size=10)
                fig_ov.update_layout(height=430)
                st.plotly_chart(fig_ov, use_container_width=True)

            with col_ov2:
                fig_ov2 = go.Figure()
                fig_ov2.add_bar(x=["กทพ. (7 สายทาง)", "กรมทางหลวง (M6/M7/M81)"],
                                y=[exat_easypass, doh_easypass],
                                name="Easy Pass", marker_color="#0B5ED7",
                                text=[exat_easypass, doh_easypass],
                                textposition="inside", texttemplate="%{text:,.0f}")
                fig_ov2.add_bar(x=["กทพ. (7 สายทาง)", "กรมทางหลวง (M6/M7/M81)"],
                                y=[exat_mpass, doh_mpass],
                                name="M-Pass", marker_color="#F57C00",
                                text=[exat_mpass, doh_mpass],
                                textposition="inside", texttemplate="%{text:,.0f}")
                fig_ov2.add_bar(x=["ดอนเมืองโทลล์เวย์"], y=[toll_easypass],
                                name="Easy Pass (Tollway)", marker_color="#0B5ED7",
                                text=[toll_easypass], textposition="inside", texttemplate="%{text:,.0f}")
                fig_ov2.add_bar(x=["ดอนเมืองโทลล์เวย์"], y=[toll_non_ep],
                                name="Non-EP (Tollway)", marker_color="#B0BEC5",
                                text=[toll_non_ep], textposition="inside", texttemplate="%{text:,.0f}")
                fig_ov2.update_layout(
                    barmode="stack",
                    title="เปรียบเทียบ Easy Pass vs M-Pass / Non-EP แยก 3 ระบบ",
                    height=430, yaxis_title="เที่ยว",
                    legend=dict(orientation="h", y=1.12),
                    plot_bgcolor="#FAFBFC"
                )
                st.plotly_chart(fig_ov2, use_container_width=True)

            st.markdown("**📋 ตารางสรุป 3 ระบบ**")
            ov_summary = pd.DataFrame({
                "ตัวชี้วัด": [
                    "ปริมาณธุรกรรมรวม", "Easy Pass (เที่ยว)", "M-Pass (เที่ยว)",
                    "สัดส่วน Easy Pass (%)", "สัดส่วน M-Pass (%)",
                    "เฉลี่ยต่อวัน (เที่ยว)", "ฐานการเปรียบเทียบ"
                ],
                "🏙️ กทพ.": [
                    f"{exat_total:,.0f}", f"{exat_easypass:,.0f}", f"{exat_mpass:,.0f}",
                    f"{exat_easypass_pct:.2f}%", f"{exat_mpass_pct:.2f}%",
                    f"{exat_avg_daily:,.0f}", "EP vs MP ✅"
                ],
                "🛤️ กรมทางหลวง": [
                    f"{doh_total:,.0f}", f"{doh_easypass:,.0f}", f"{doh_mpass:,.0f}",
                    f"{doh_easypass_pct:.2f}%", f"{doh_mpass_pct:.2f}%",
                    f"{doh_avg_daily:,.0f}", "EP vs MP ✅"
                ],
                "🏙️ ดอนเมืองโทลล์เวย์": [
                    f"{toll_total_tw:,.0f}", f"{toll_easypass:,.0f}", "— ไม่มี —",
                    f"{toll_pct:.2f}%", "— ไม่มี —",
                    f"{toll_total_tw/month_days(tollway_detail):,.0f}", "EP vs Total ⚠️"
                ]
            })
            st.dataframe(ov_summary, use_container_width=True, hide_index=True)
            st.markdown("---")

            # ===== SECTION 1: กทพ. 7 สายทาง =====
            st.markdown(section_title("🏙️ ส่วนที่ 1: กทพ. 7 สายทาง", "หน้า 9", "กทพ. เท่านั้น"), unsafe_allow_html=True)

            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            with r1c1:
                st.markdown(kpi_tile("📊 รวม 7 สายทาง", f"{exat_total:,.0f}", "เที่ยว", color="teal"), unsafe_allow_html=True)
            with r1c2:
                st.markdown(kpi_tile("🔵 Easy Pass", f"{exat_easypass:,.0f}", f"{exat_easypass_pct:.2f}%", color="blue"), unsafe_allow_html=True)
            with r1c3:
                st.markdown(kpi_tile("🟠 M-Pass", f"{exat_mpass:,.0f}", f"{exat_mpass_pct:.2f}%", color="orange"), unsafe_allow_html=True)
            with r1c4:
                st.markdown(kpi_tile("📈 เฉลี่ย/วัน", f"{exat_avg_daily:,.0f}", "เที่ยว/วัน", color="green"), unsafe_allow_html=True)

            col_x1, col_x2 = st.columns([1.4, 1])
            with col_x1:
                fig_exat = go.Figure()
                fig_exat.add_bar(x=exat_routes["route_name"], y=exat_routes["easypass_transactions"],
                                  name="Easy Pass", marker_color="#0B5ED7")
                fig_exat.add_bar(x=exat_routes["route_name"], y=exat_routes["mpass_transactions"],
                                  name="M-Pass", marker_color="#F57C00")
                fig_exat.update_layout(barmode="stack",
                                        title="Easy Pass vs M-Pass — 7 สายทาง กทพ.",
                                        height=430, xaxis_tickangle=-20,
                                        yaxis_title="เที่ยว",
                                        legend=dict(orientation="h", y=1.12),
                                        plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_exat, use_container_width=True)
            with col_x2:
                pie_exat = pd.DataFrame({"ประเภท": ["Easy Pass", "M-Pass"], "ปริมาณ": [exat_easypass, exat_mpass]})
                fig_pe = px.pie(pie_exat, names="ประเภท", values="ปริมาณ",
                                 title="สัดส่วน Easy Pass / M-Pass (กทพ.)",
                                 color="ประเภท",
                                 color_discrete_map={"Easy Pass": "#0B5ED7", "M-Pass": "#F57C00"},
                                 hole=0.5)
                fig_pe.update_traces(textinfo="label+percent+value",
                                      texttemplate="%{label}<br>%{percent}<br>(%{value:,.0f})",
                                      textfont_size=11)
                fig_pe.update_layout(height=430)
                st.plotly_chart(fig_pe, use_container_width=True)

            ex_disp = exat_routes[["route_name", "mpass_transactions", "mpass_percent",
                                    "easypass_transactions", "easypass_percent",
                                    "total_transactions", "avg_daily"]].copy()
            ex_disp.columns = ["สายทาง", "M-Pass", "%MP", "Easy Pass", "%EP", "รวม", "เฉลี่ย/วัน"]
            for c in ["M-Pass", "Easy Pass", "รวม", "เฉลี่ย/วัน"]:
                ex_disp[c] = ex_disp[c].apply(lambda x: f"{x:,.0f}")
            for c in ["%MP", "%EP"]:
                ex_disp[c] = ex_disp[c].apply(lambda x: f"{x:.2f}%")
            st.dataframe(ex_disp, use_container_width=True, hide_index=True)
            st.markdown("---")

            # ===== SECTION 2: กรมทางหลวง =====
            st.markdown(section_title("🛤️ ส่วนที่ 2: กรมทางหลวง (M6/M7/M81)", "หน้า 9", "กรมทางหลวง"), unsafe_allow_html=True)

            d1, d2, d3, d4 = st.columns(4)
            with d1:
                st.markdown(kpi_tile("📊 รวมกรมทางหลวง", f"{doh_total:,.0f}", "เที่ยว", color="teal"), unsafe_allow_html=True)
            with d2:
                st.markdown(kpi_tile("🔵 Easy Pass", f"{doh_easypass:,.0f}", f"{doh_easypass_pct:.2f}%", color="blue"), unsafe_allow_html=True)
            with d3:
                st.markdown(kpi_tile("🟠 M-Pass", f"{doh_mpass:,.0f}", f"{doh_mpass_pct:.2f}%", color="orange"), unsafe_allow_html=True)
            with d4:
                st.markdown(kpi_tile("📈 เฉลี่ย/วัน", f"{doh_avg_daily:,.0f}", "เที่ยว/วัน", color="green"), unsafe_allow_html=True)

            if not doh_routes.empty:
                col_d1, col_d2 = st.columns([1.4, 1])
                with col_d1:
                    fig_doh = go.Figure()
                    fig_doh.add_bar(x=doh_routes["route_name"], y=doh_routes["easypass_transactions"],
                                     name="Easy Pass", marker_color="#0B5ED7")
                    fig_doh.add_bar(x=doh_routes["route_name"], y=doh_routes["mpass_transactions"],
                                     name="M-Pass", marker_color="#F57C00")
                    fig_doh.update_layout(barmode="stack",
                                           title="Easy Pass vs M-Pass — กรมทางหลวง",
                                           height=430, xaxis_tickangle=-20,
                                           yaxis_title="เที่ยว",
                                           legend=dict(orientation="h", y=1.12),
                                           plot_bgcolor="#FAFBFC")
                    st.plotly_chart(fig_doh, use_container_width=True)
                with col_d2:
                    pie_doh = pd.DataFrame({"ประเภท": ["Easy Pass", "M-Pass"], "ปริมาณ": [doh_easypass, doh_mpass]})
                    fig_pd = px.pie(pie_doh, names="ประเภท", values="ปริมาณ",
                                     title="สัดส่วน Easy Pass / M-Pass (ทล.)",
                                     color="ประเภท",
                                     color_discrete_map={"Easy Pass": "#0B5ED7", "M-Pass": "#F57C00"},
                                     hole=0.5)
                    fig_pd.update_traces(textinfo="label+percent+value",
                                          texttemplate="%{label}<br>%{percent}<br>(%{value:,.0f})",
                                          textfont_size=11)
                    fig_pd.update_layout(height=430)
                    st.plotly_chart(fig_pd, use_container_width=True)

                doh_disp = doh_routes[["route_name", "mpass_transactions", "mpass_percent",
                                        "easypass_transactions", "easypass_percent",
                                        "total_transactions", "avg_daily"]].copy()
                doh_disp.columns = ["สายทาง", "M-Pass", "%MP", "Easy Pass", "%EP", "รวม", "เฉลี่ย/วัน"]
                for c in ["M-Pass", "Easy Pass", "รวม", "เฉลี่ย/วัน"]:
                    doh_disp[c] = doh_disp[c].apply(lambda x: f"{x:,.0f}")
                for c in ["%MP", "%EP"]:
                    doh_disp[c] = doh_disp[c].apply(lambda x: f"{x:.2f}%")
                st.dataframe(doh_disp, use_container_width=True, hide_index=True)
            st.markdown("---")

            # ===== SECTION 3: ดอนเมืองโทลล์เวย์ =====
            st.markdown(section_title("🏙️ ส่วนที่ 3: ดอนเมืองโทลล์เวย์", "หน้า 10", "ดอนเมืองโทลล์เวย์"), unsafe_allow_html=True)

            st.markdown("""
            <div class="warning-banner">
                ⚠️ <b>หมายเหตุ:</b> ดอนเมืองโทลล์เวย์ไม่มีข้อมูล M-Pass
                จึงต้องเปรียบเทียบเป็น <b>Easy Pass vs ปริมาณทั้งหมด</b> แยกออกจาก 2 ระบบข้างต้น
            </div>
            """, unsafe_allow_html=True)

            if has_easypass_tw:
                t1, t2, t3, t4 = st.columns(4)
                with t1:
                    st.markdown(kpi_tile("📊 ปริมาณทั้งหมด", f"{toll_total_tw:,.0f}", "เที่ยว", color="teal"), unsafe_allow_html=True)
                with t2:
                    st.markdown(kpi_tile("🔵 Easy Pass", f"{toll_easypass:,.0f}", f"{toll_pct:.2f}%", color="blue"), unsafe_allow_html=True)
                with t3:
                    st.markdown(kpi_tile("🟠 Non-Easy Pass", f"{toll_non_ep:,.0f}", f"{100-toll_pct:.2f}%", color="orange"), unsafe_allow_html=True)
                with t4:
                    st.markdown(kpi_tile("📈 เฉลี่ย/วัน", f"{toll_total_tw/month_days(tollway_detail):,.0f}", "เที่ยว/วัน", color="green"), unsafe_allow_html=True)

                col_tw1, col_tw2 = st.columns([1.4, 1])
                with col_tw1:
                    fig_tw = go.Figure()
                    fig_tw.add_bar(x=tollway_detail["month_label"],
                                    y=tollway_detail["total_tollway_transactions"],
                                    name="ปริมาณทั้งหมด", marker_color="#B0BEC5")
                    fig_tw.add_bar(x=tollway_detail["month_label"],
                                    y=tollway_detail["easypass_tollway_transactions"],
                                    name="Easy Pass", marker_color="#0B5ED7")
                    fig_tw.add_trace(go.Scatter(x=tollway_detail["month_label"],
                                                  y=tollway_detail["easypass_percent"],
                                                  name="% Easy Pass", yaxis="y2",
                                                  line=dict(color="#F57C00", width=3),
                                                  marker=dict(size=9)))
                    fig_tw.update_layout(barmode="group",
                                          title="ดอนเมืองโทลล์เวย์ — Easy Pass vs ทั้งหมด",
                                          height=430, yaxis=dict(title="เที่ยว"),
                                          yaxis2=dict(title="ร้อยละ (%)", overlaying="y", side="right"),
                                          legend=dict(orientation="h", y=1.12),
                                          plot_bgcolor="#FAFBFC")
                    st.plotly_chart(fig_tw, use_container_width=True)
                with col_tw2:
                    pie_tw = pd.DataFrame({"ประเภท": ["Easy Pass", "Non-Easy Pass"], "ปริมาณ": [toll_easypass, toll_non_ep]})
                    fig_pt = px.pie(pie_tw, names="ประเภท", values="ปริมาณ",
                                     title="สัดส่วน Easy Pass / Non-EP (Tollway)",
                                     color="ประเภท",
                                     color_discrete_map={"Easy Pass": "#0B5ED7", "Non-Easy Pass": "#B0BEC5"},
                                     hole=0.5)
                    fig_pt.update_traces(textinfo="label+percent+value",
                                          texttemplate="%{label}<br>%{percent}<br>(%{value:,.0f})",
                                          textfont_size=11)
                    fig_pt.update_layout(height=430)
                    st.plotly_chart(fig_pt, use_container_width=True)

                st.markdown("**📋 ตารางรายเดือน**")
                tw = tollway_detail.copy()
                tw["total_tollway_transactions"] = tw["total_tollway_transactions"].apply(lambda x: f"{x:,.0f}")
                tw["easypass_tollway_transactions"] = tw["easypass_tollway_transactions"].apply(lambda x: f"{x:,.0f}")
                tw["easypass_percent"] = tw["easypass_percent"].apply(lambda x: f"{x:.2f}%")
                tw = tw[["month_label", "total_tollway_transactions", "easypass_tollway_transactions", "easypass_percent"]]
                tw.columns = ["เดือน", "รวม", "Easy Pass", "% Easy Pass"]
                st.dataframe(tw, use_container_width=True, hide_index=True)
            st.markdown("---")

            # ===== SECTION 4: Comparable Basis =====
            st.markdown(section_title("⚖️ ส่วนที่ 4: เปรียบเทียบ Comparable Basis (กทพ. vs กรมทางหลวง)", "หน้า 12", "เฉพาะ กทพ. + ทล."), unsafe_allow_html=True)

            st.markdown("""
            <div class="method-banner">
                🎯 <b>หลักการ:</b> เปรียบเทียบเฉพาะ <b>กทพ. vs กรมทางหลวง</b> เท่านั้น
                เพราะมีโครงสร้างข้อมูลเหมือนกัน (Easy Pass + M-Pass)<br>
                ⚠️ <b>ไม่นำดอนเมืองโทลล์เวย์เข้าร่วม</b> — เนื่องจากมีเฉพาะ Easy Pass (เปรียบเทียบจะไม่ยุติธรรม)
            </div>
            """, unsafe_allow_html=True)

            cc1, cc2, cc3 = st.columns(3)
            cmp_total = exat_total + doh_total
            exat_pct_of_cmp = safe_pct(exat_total, cmp_total)
            doh_pct_of_cmp = safe_pct(doh_total, cmp_total)

            with cc1:
                st.markdown(f"""
                <div class="compare-tile" style="border-left:5px solid #0B5ED7;">
                    <div class="ct-icon">🏙️</div>
                    <div class="ct-label">กทพ. (7 สายทาง)</div>
                    <div class="ct-value">{exat_total:,.0f}</div>
                    <div class="ct-sub">เที่ยว • <b>{exat_pct_of_cmp:.1f}%</b></div>
                </div>
                """, unsafe_allow_html=True)
            with cc2:
                st.markdown(f"""
                <div class="compare-tile" style="border-left:5px solid #F57C00;">
                    <div class="ct-icon">🛤️</div>
                    <div class="ct-label">กรมทางหลวง (M6/M7/M81)</div>
                    <div class="ct-value">{doh_total:,.0f}</div>
                    <div class="ct-sub">เที่ยว • <b>{doh_pct_of_cmp:.1f}%</b></div>
                </div>
                """, unsafe_allow_html=True)
            with cc3:
                st.markdown(f"""
                <div class="compare-tile" style="border-left:5px solid #2E7D32;">
                    <div class="ct-icon">📊</div>
                    <div class="ct-label">รวม กทพ. + ทล.</div>
                    <div class="ct-value">{cmp_total:,.0f}</div>
                    <div class="ct-sub">เที่ยว • 100%</div>
                </div>
                """, unsafe_allow_html=True)

            fig_cmp = go.Figure()
            fig_cmp.add_bar(x=["กทพ. (7 สายทาง)", "กรมทางหลวง"], y=[exat_easypass, doh_easypass],
                            name="Easy Pass", marker_color="#0B5ED7",
                            text=[exat_easypass, doh_easypass],
                            textposition="inside", texttemplate="%{text:,.0f}")
            fig_cmp.add_bar(x=["กทพ. (7 สายทาง)", "กรมทางหลวง"], y=[exat_mpass, doh_mpass],
                            name="M-Pass", marker_color="#F57C00",
                            text=[exat_mpass, doh_mpass],
                            textposition="inside", texttemplate="%{text:,.0f}")
            fig_cmp.update_layout(barmode="stack",
                                   title="เปรียบเทียบ Easy Pass vs M-Pass: กทพ. vs กรมทางหลวง",
                                   height=430, yaxis_title="เที่ยว",
                                   legend=dict(orientation="h", y=1.12),
                                   plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig_cmp, use_container_width=True)

            st.markdown("**📋 ตารางเปรียบเทียบ**")
            summary_cmp = pd.DataFrame({
                "ตัวชี้วัด": ["ปริมาณธุรกรรมรวม", "Easy Pass", "M-Pass",
                             "สัดส่วน Easy Pass", "สัดส่วน M-Pass", "เฉลี่ยต่อวัน"],
                "🏙️ กทพ.": [
                    f"{exat_total:,.0f}", f"{exat_easypass:,.0f}", f"{exat_mpass:,.0f}",
                    f"{exat_easypass_pct:.2f}%", f"{exat_mpass_pct:.2f}%",
                    f"{exat_avg_daily:,.0f}"
                ],
                "🛤️ กรมทางหลวง": [
                    f"{doh_total:,.0f}", f"{doh_easypass:,.0f}", f"{doh_mpass:,.0f}",
                    f"{doh_easypass_pct:.2f}%", f"{doh_mpass_pct:.2f}%",
                    f"{doh_avg_daily:,.0f}"
                ],
                "ผลต่าง (กทพ. - ทล.)": [
                    f"{exat_total - doh_total:+,.0f}",
                    f"{exat_easypass - doh_easypass:+,.0f}",
                    f"{exat_mpass - doh_mpass:+,.0f}",
                    f"{exat_easypass_pct - doh_easypass_pct:+.2f} pp",
                    f"{exat_mpass_pct - doh_mpass_pct:+.2f} pp",
                    f"{exat_avg_daily - doh_avg_daily:+,.0f}"
                ]
            })
            st.dataframe(summary_cmp, use_container_width=True, hide_index=True)
            st.markdown("---")

            # ===== SECTION 5: Interpretation =====
            st.markdown(section_title("💡 ส่วนที่ 5: Interpretation จากข้อมูล"), unsafe_allow_html=True)
            cmp_total = exat_total + doh_total
            combined_ep = exat_easypass + doh_easypass
            combined_mp = exat_mpass + doh_mpass
            exat_route_top = exat_routes.sort_values("total_transactions", ascending=False).iloc[0] if not exat_routes.empty else None
            doh_route_top = doh_routes.sort_values("total_transactions", ascending=False).iloc[0] if not doh_routes.empty else None
            bullets = [
                f"ฐานธุรกรรมที่เปรียบเทียบได้ระหว่าง กทพ. + กรมทางหลวงมี {cmp_total:,.0f} เที่ยว โดย กทพ. คิดเป็น {safe_pct(exat_total, cmp_total):.1f}% และกรมทางหลวง {safe_pct(doh_total, cmp_total):.1f}%",
                f"เมื่อรวมเฉพาะ 2 ระบบที่มีฐานเปรียบเทียบเดียวกัน Easy Pass มีสัดส่วน {safe_pct(combined_ep, cmp_total):.1f}% และ M-Pass {safe_pct(combined_mp, cmp_total):.1f}%",
                f"สัดส่วน Easy Pass ของ กทพ. อยู่ที่ {exat_easypass_pct:.2f}% เทียบกับกรมทางหลวง {doh_easypass_pct:.2f}% ต่างกัน {exat_easypass_pct-doh_easypass_pct:+.2f} pp",
                (f"สายทางของ กทพ. ที่มีธุรกรรมรวมสูงสุดคือ <b>{exat_route_top['route_name']}</b> {exat_route_top['total_transactions']:,.0f} เที่ยว" if exat_route_top is not None else None),
                (f"สายทางของกรมทางหลวงที่มีธุรกรรมรวมสูงสุดคือ <b>{doh_route_top['route_name']}</b> {doh_route_top['total_transactions']:,.0f} เที่ยว" if doh_route_top is not None else None),
                f"ดอนเมืองโทลล์เวย์มี Easy Pass {toll_pct:.2f}% ของธุรกรรมทั้งหมด และควรอ่านแยกจากการเปรียบเทียบ EP/MP เนื่องจากไม่มี M-Pass ในฐานข้อมูลชุดนี้"
            ]
            st.markdown(html_interpretation("ธุรกรรม Easy Pass / M-Pass", bullets,
                "เป็น descriptive interpretation จากปริมาณและสัดส่วน ไม่ได้สรุปประสิทธิภาพหรือสาเหตุจากข้อมูลเพียงชุดเดียว"), unsafe_allow_html=True)


# =============================================================================
# TAB: 💰 ยอดเติมเงินสำรอง
# =============================================================================
if tab_topup is not None:
    with tab_topup:
        st.markdown(section_title(f"💰 5.1 ยอดเติมเงินสำรองค่าผ่านทาง ประจำเดือน {LATEST_MONTH}", "หน้า 10"), unsafe_allow_html=True)

        if n_error == 0 and not topup_total.empty:
            tp_curr = topup_total["total_baht"].iloc[-1]
            tp_prev = topup_total["total_baht"].iloc[-2]
            tp_chg = pct_change(tp_curr, tp_prev)
            ext_curr = topup_total["external_agencies_baht"].iloc[-1]
            int_curr = topup_total["internal_baht"].iloc[-1]

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(kpi_tile("💰 ยอดเติมเงินเดือนนี้", f"{tp_curr/1e6:,.1f} ลบ.", f"{tp_chg:+.1f}% MoM", color="green"), unsafe_allow_html=True)
            with k2:
                st.markdown(kpi_tile("🏢 หน่วยงานภายนอก", f"{ext_curr/1e6:,.1f} ลบ.", f"{safe_pct(ext_curr, tp_curr):.1f}%", color="blue"), unsafe_allow_html=True)
            with k3:
                st.markdown(kpi_tile("🏛️ หน่วยงานภายใน", f"{int_curr/1e6:,.1f} ลบ.", f"{safe_pct(int_curr, tp_curr):.1f}%", color="purple"), unsafe_allow_html=True)
            with k4:
                st.markdown(kpi_tile("📅 เฉลี่ย/วัน", f"{tp_curr/month_days(topup_total)/1e6:,.2f} ลบ.", "บาท/วัน", color="orange"), unsafe_allow_html=True)
            st.markdown("---")

        st.markdown(sub_section_title("📈 แนวโน้มรายเดือน — แยกช่องทาง"), unsafe_allow_html=True)
        fig = px.area(topup_total, x="month_label",
                      y=["external_agencies_baht", "internal_baht", "other_channel_baht"],
                      title="ยอดเติมเงินรายเดือน แยกช่องทาง")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")

        st.markdown(section_title(f"📊 5.2 ยอดเติมเงินสำรองค่าผ่านทางสะสม ปีงบประมาณ 2569 (ข้อมูลสะสมถึง {LATEST_MONTH})", "หน้า 11"), unsafe_allow_html=True)
        if n_error == 0 and not topup_total.empty:
            cum_total = topup_total["total_baht"].sum()
            cum_ext = topup_total["external_agencies_baht"].sum()
            cum_int = topup_total["internal_baht"].sum()

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(kpi_tile("💰 ยอดสะสมทั้งปีงบ", f"{cum_total/1e9:,.2f} พันล้าน", f"ข้อมูลสะสมถึง {LATEST_MONTH}", color="green"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_tile("🏢 ภายนอกสะสม", f"{cum_ext/1e9:,.2f} พันล้าน", f"{safe_pct(cum_ext, cum_total):.1f}%", color="blue"), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi_tile("🏛️ ภายในสะสม", f"{cum_int/1e9:,.2f} พันล้าน", f"{safe_pct(cum_int, cum_total):.1f}%", color="purple"), unsafe_allow_html=True)
            with c4:
                tot_topup_days = sum(month_days(pd.DataFrame({'month': [m]})) for m in topup_total['month'])
                avg_topup_daily = (cum_total / tot_topup_days / 1e6) if tot_topup_days else 0
                st.markdown(kpi_tile("📅 เฉลี่ย/วัน", f"{avg_topup_daily:,.2f} ลบ.", "บาท/วัน", color="orange"), unsafe_allow_html=True)

            cum_df = topup_total.copy()
            cum_df["cum_total_baht"] = cum_df["total_baht"].cumsum()
            cum_df["cum_ext"] = cum_df["external_agencies_baht"].cumsum()
            cum_df["cum_int"] = cum_df["internal_baht"].cumsum()
            cum_df["cum_oth"] = cum_df["other_channel_baht"].cumsum()

            col_cum1, col_cum2 = st.columns([1.4, 1])
            with col_cum1:
                fig_cum = go.Figure()
                fig_cum.add_trace(go.Scatter(x=cum_df["month_label"], y=cum_df["cum_total_baht"]/1e9,
                                              name="รวมสะสม", line=dict(color="#2E7D32", width=3), mode="lines+markers"))
                fig_cum.add_trace(go.Scatter(x=cum_df["month_label"], y=cum_df["cum_ext"]/1e9,
                                              name="ภายนอกสะสม", line=dict(color="#0B5ED7", width=2.5), mode="lines+markers"))
                fig_cum.add_trace(go.Scatter(x=cum_df["month_label"], y=cum_df["cum_int"]/1e9,
                                              name="ภายในสะสม", line=dict(color="#6A1B9A", width=2.5), mode="lines+markers"))
                fig_cum.update_layout(title="ยอดเติมเงินสะสมปีงบ 2569", height=430,
                                       yaxis_title="พันล้านบาท", legend=dict(orientation="h", y=1.12),
                                       plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_cum, use_container_width=True)
            with col_cum2:
                cum_disp = cum_df.copy()
                for c in ["cum_total_baht", "cum_ext", "cum_int", "cum_oth"]:
                    cum_disp[c] = cum_disp[c].apply(lambda x: f"{x/1e6:,.1f}")
                cum_disp = cum_disp[["month_label", "cum_total_baht", "cum_ext", "cum_int", "cum_oth"]]
                cum_disp.columns = ["เดือน", "รวม (ลบ.)", "ภายนอก", "ภายใน", "อื่นๆ"]
                st.dataframe(cum_disp, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

        st.markdown(section_title("💳 5.3 ยอดเติมเงินด้วยเครื่อง EDC ปีงบประมาณ 2569", "หน้า 12"), unsafe_allow_html=True)
        if n_error == 0 and not topup_edc.empty:
            fig_edc = px.bar(topup_edc, x="month_label", y=["cash_baht", "credit_baht", "debit_baht", "qr_baht"], barmode="stack")
            fig_edc.update_layout(height=430, yaxis_title="บาท", legend=dict(orientation="h", y=1.12),
                                   plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig_edc, use_container_width=True)

            edc_sum = pd.DataFrame({
                "ช่องทาง": ["เงินสด (Cash)", "บัตรเครดิต (Credit)", "บัตรเดบิต (Debit)", "QR Code"],
                "ยอดสะสมปีงบ (บาท)": [
                    f"{topup_edc['cash_baht'].sum():,.0f}",
                    f"{topup_edc['credit_baht'].sum():,.0f}",
                    f"{topup_edc['debit_baht'].sum():,.0f}",
                    f"{topup_edc['qr_baht'].sum():,.0f}",
                ],
            })
            st.dataframe(edc_sum, use_container_width=True, hide_index=True)
            st.markdown("---")

        st.markdown(section_title("🏢 5.4 การเติมเงินผ่านหน่วยงานภายนอก (Top 16)", "หน้า 13"), unsafe_allow_html=True)
        if n_error == 0 and not topup_ext.empty:
            col_ext1, col_ext2 = st.columns([1.3, 1])
            with col_ext1:
                fig_ext = px.bar(topup_ext.sort_values("amount_baht"), x="amount_baht", y="agency",
                                  orientation="h", text="amount_baht", color="amount_baht",
                                  color_continuous_scale="Blues")
                fig_ext.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_ext.update_layout(height=520, showlegend=False, coloraxis_showscale=False,
                                       yaxis_title="", xaxis_title="ยอดเติมเงิน (บาท)")
                st.plotly_chart(fig_ext, use_container_width=True)
            with col_ext2:
                ext_disp = topup_ext.copy()
                ext_disp["amount_baht"] = ext_disp["amount_baht"].apply(lambda x: f"{x:,.0f}")
                ext_disp["share_percent"] = ext_disp["share_percent"].apply(lambda x: f"{x:.2f}%")
                ext_disp.columns = ["หน่วยงาน", "ยอดเติมเงิน (บาท)", "สัดส่วน"]
                st.dataframe(ext_disp, use_container_width=True, hide_index=True, height=520)
            st.markdown("---")

        st.markdown(section_title(f"📊 5.5 สรุปยอดการเติมเงิน ตามช่องทาง ประจำเดือน {LATEST_MONTH}", "หน้า 14"), unsafe_allow_html=True)
        if n_error == 0 and not topup_channel.empty:
            col_tc1, col_tc2 = st.columns(2)
            with col_tc1:
                fig_ch = px.pie(topup_channel, names="channel", values="amount_baht", hole=0.4,
                                 title="สัดส่วนยอดเงินตามช่องทาง")
                fig_ch.update_traces(textinfo="label+percent", textfont_size=10)
                fig_ch.update_layout(height=430)
                st.plotly_chart(fig_ch, use_container_width=True)
            with col_tc2:
                fig_ch2 = px.bar(topup_channel, x="channel", y="transactions", text="transactions",
                                  color="channel", title="จำนวนรายการตามช่องทาง")
                fig_ch2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_ch2.update_layout(showlegend=False, xaxis_tickangle=-30, height=430)
                st.plotly_chart(fig_ch2, use_container_width=True)

            tc_disp = topup_channel.copy()
            tc_disp["transactions"] = tc_disp["transactions"].apply(lambda x: f"{x:,.0f}")
            tc_disp["percent_transactions"] = tc_disp["percent_transactions"].apply(lambda x: f"{x:.2f}%")
            tc_disp["amount_baht"] = tc_disp["amount_baht"].apply(lambda x: f"{x:,.0f}")
            tc_disp["percent_amount"] = tc_disp["percent_amount"].apply(lambda x: f"{x:.2f}%")
            tc_disp.columns = ["ช่องทาง", "จำนวนรายการ", "% รายการ", "ยอดเงิน (บาท)", "% ยอดเงิน"]
            st.dataframe(tc_disp, use_container_width=True, hide_index=True)
            st.markdown("---")

        st.markdown(section_title(f"🌐 5.6 การเติมเงินผ่าน EXAT Portal และ www.thaieasypass.com ประจำเดือน {LATEST_MONTH}", "หน้า 15"), unsafe_allow_html=True)
        if n_error == 0 and not topup_digital.empty:
            latest_dig = topup_digital.iloc[-1]
            dig_tx = latest_dig["transactions"]
            dig_amt = latest_dig["amount_baht"]

            st.markdown(f"""
            <div class="info-banner">
                📖 EXAT Portal Application + www.thaieasypass.com รวม <b>{dig_tx:,.0f} รายการ</b>
                ยอดเงิน <b>{dig_amt:,.0f} บาท</b> (ข้อมูลเดือน {latest_dig['month_label']})
            </div>
            """, unsafe_allow_html=True)

            d1, d2 = st.columns(2)
            with d1:
                st.markdown(kpi_tile("📱 + 🌐 Digital Channels", f"{dig_tx:,.0f} รายการ", "EXAT Portal + Website", color="blue"), unsafe_allow_html=True)
            with d2:
                st.markdown(kpi_tile("💰 ยอดรวม Digital", f"{dig_amt:,.0f} บาท", "ข้อมูลเดือนล่าสุด", color="purple"), unsafe_allow_html=True)
            st.markdown("---")

            col_dig1, col_dig2 = st.columns([1.4, 1])
            with col_dig1:
                # ---------- คำนวณ MoM Growth ----------
                df_dig = topup_digital.copy().reset_index(drop=True)
                df_dig["growth_pct"] = df_dig["amount_baht"].pct_change() * 100

                # ---------- สร้างกราฟ ----------
                fig_dig = go.Figure()

                # แท่ง Bar: ยอดเงิน + ตัวเลขแนวตั้งกลางแท่ง
                fig_dig.add_trace(go.Bar(
                    x=df_dig["month_label"],
                    y=df_dig["amount_baht"],
                    name="ยอดเงิน (บาท)",
                    marker_color="#FFD9A0",
                    marker_line_color="#E0A040",
                    marker_line_width=1,
                    text=df_dig["amount_baht"].apply(lambda x: f"{x:,.0f}"),
                    textposition="inside",
                    insidetextanchor="middle",
                    textangle=-90,
                    textfont=dict(size=8, color="#8B4513"),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "ยอดเงิน: %{y:,.0f} บาท<br>"
                        "<extra></extra>"
                    ),
                ))

                # ---------- Growth Badges บนยอดแท่ง ----------
                for _, row in df_dig.iterrows():
                    g = row["growth_pct"]
                    if pd.isna(g):
                        continue  # ข้ามเดือนแรก (ไม่มี growth)

                    # สีตามเครื่องหมาย
                    if g > 0:
                        arrow, bg, fg, bd = "▲", "#A5D6A7", "#1B5E20", "#66BB6A"
                    elif g < 0:
                        arrow, bg, fg, bd = "▼", "#EF9A9A", "#B71C1C", "#E57373"
                    else:
                        arrow, bg, fg, bd = "●", "#E0E0E0", "#424242", "#BDBDBD"

                    fig_dig.add_annotation(
                        x=row["month_label"],
                        y=row["amount_baht"] * 1.03,
                        text=f"<b>{arrow} {g:+.2f}%</b>",
                        showarrow=False,
                        bgcolor=bg,
                        bordercolor=bd,
                        borderwidth=1,
                        borderpad=3,
                        font=dict(size=9, color=fg),
                        xanchor="center",
                        yanchor="bottom",
                    )

                fig_dig.update_layout(
                    title="ยอดเติมเงินผ่าน EXAT Portal + Website (รายเดือน)",
                    height=480,
                    yaxis=dict(
                        title="ยอดเงิน (บาท)",
                        gridcolor="#E0E6ED",
                        tickformat=",.0f",
                    ),
                    xaxis=dict(
                        title="เดือน",
                        tickangle=-45,
                    ),
                    showlegend=False,
                    plot_bgcolor="#FAFBFC",
                    margin=dict(t=60, b=100, l=70, r=20),
                )
                st.plotly_chart(fig_dig, use_container_width=True)
            with col_dig2:
                dig_disp = topup_digital.copy()
                dig_disp["transactions"] = dig_disp["transactions"].apply(lambda x: f"{x:,.0f}")
                dig_disp["amount_baht"] = dig_disp["amount_baht"].apply(lambda x: f"{x:,.0f}")
                dig_disp = dig_disp[["month_label", "transactions", "amount_baht"]]
                dig_disp.columns = ["เดือน", "รายการ", "ยอดเงิน (บาท)"]
                st.dataframe(dig_disp, use_container_width=True, hide_index=True, height=430)
            st.markdown("---")

# =============================================================================

            st.markdown(sub_section_title("💡 Interpretation — ยอดเติมเงินสำรอง"), unsafe_allow_html=True)
            tp_share_ext = safe_pct(ext_curr, tp_curr)
            tp_share_int = safe_pct(int_curr, tp_curr)
            bullets = [
                f"ยอดเติมเงินเดือนล่าสุด {tp_curr/1e6:,.2f} ล้านบาท เปลี่ยนแปลง {tp_chg:+.1f}% จากเดือนก่อน",
                f"โครงสร้างยอดเติมเงินล่าสุดแบ่งเป็นหน่วยงานภายนอก {tp_share_ext:.1f}% และหน่วยงานภายใน {tp_share_int:.1f}% ตามข้อมูลที่รายงาน",
                f"ยอดเติมเงินสะสมของชุดข้อมูลอยู่ที่ {cum_total/1e9:,.2f} พันล้านบาท โดยสัดส่วนภายนอก {safe_pct(cum_ext,cum_total):.1f}% และภายใน {safe_pct(cum_int,cum_total):.1f}%",
                "ข้อมูลช่องทางช่วยให้เห็นโครงสร้างของธุรกรรม แต่ไม่ควรตีความว่าช่องทางที่มีมูลค่าสูงกว่ามีประสิทธิภาพสูงกว่าหากยังไม่มีข้อมูลต้นทุนหรือจำนวนผู้ใช้เป็นฐานประกอบ",
                "ข้อมูล Digital ในชุดข้อมูลเป็นยอดรวม EXAT Portal + Website จึงไม่ควรแยกสัดส่วนรายช่องทางจากค่าประมาณที่ไม่ได้อยู่ในไฟล์"
            ]
            st.markdown(html_interpretation("ยอดเติมเงินสำรอง", bullets), unsafe_allow_html=True)

# TAB: 🌐 สถิติเว็บไซต์
# =============================================================================
if tab_web is not None:
    with tab_web:
        st.markdown(section_title("🌐 6. สถิติการสมัครสมาชิกเว็บไซต์ www.thaieasypass.com", "หน้า 16"), unsafe_allow_html=True)
        st.markdown("""<div class="info-banner">
            📖 <b>สถิติการสมัครสมาชิก</b> = จำนวนบัญชีที่สมัครใหม่บนเว็บไซต์ thaieasypass<br>
            🔴 เส้นทึบ = ยอดสะสมทั้งหมด &nbsp;•&nbsp; 🟢 เส้นประ = ยอดสมัครใหม่รายเดือน
        </div>""", unsafe_allow_html=True)

        if n_error == 0 and not website.empty:
            w_new_curr = website["new_registrations"].iloc[-1]
            w_new_prev = website["new_registrations"].iloc[-2] if len(website) > 1 else 0
            w_new_chg = pct_change(w_new_curr, w_new_prev)
            w_cum_curr = website["cumulative_total"].iloc[-1]
            w_new_avg = website["new_registrations"].mean()
            w_new_max = website["new_registrations"].max()
            w_new_max_month = website.loc[website["new_registrations"].idxmax(), "month_label"]
            w_new_total = website["new_registrations"].sum()
            w_cum_first = website["cumulative_total"].iloc[0]
            w_cum_growth = safe_pct(w_cum_curr - w_cum_first, w_cum_first)

            # ---------- KPI Tiles ----------
            w1, w2, w3, w4 = st.columns(4)
            with w1:
                st.markdown(kpi_tile("📅 สมัครใหม่เดือนนี้", f"{w_new_curr:,.0f}",
                                      f"{w_new_chg:+.1f}% MoM",
                                      color="green",
                                      delta_dir="up" if w_new_chg >= 0 else "down"),
                            unsafe_allow_html=True)
            with w2:
                st.markdown(kpi_tile("👥 สมาชิกสะสมทั้งหมด", f"{w_cum_curr:,.0f}",
                                      f"{w_cum_growth:+.1f}% ในช่วง {len(website)} เดือน",
                                      color="red"),
                            unsafe_allow_html=True)
            with w3:
                st.markdown(kpi_tile("📊 เฉลี่ย/เดือน", f"{w_new_avg:,.0f}",
                                      f"บัญชี/เดือน ({len(website)} เดือน)",
                                      color="blue"),
                            unsafe_allow_html=True)
            with w4:
                st.markdown(kpi_tile("🏆 สูงสุด", f"{w_new_max:,.0f}",
                                      f"เดือน {w_new_max_month}",
                                      color="orange"),
                            unsafe_allow_html=True)
            st.markdown("---")

            # ---------- Dual-axis Chart ----------
            wf = website.copy().reset_index(drop=True)
            wf["growth_pct"] = wf["new_registrations"].pct_change() * 100

            fig_web = go.Figure()

            # Bar: new registrations (ซ้าย)
            fig_web.add_trace(go.Bar(
                x=wf["month_label"],
                y=wf["new_registrations"],
                name="สมัครใหม่/เดือน (บัญชี)",
                marker_color="#A5D6A7",
                marker_line_color="#66BB6A",
                marker_line_width=1,
                text=wf["new_registrations"].apply(lambda x: f"{x:,.0f}"),
                textposition="outside",
                textfont=dict(size=9, color="#1B5E20"),
                yaxis="y",
                hovertemplate="<b>%{x}</b><br>สมัครใหม่: %{y:,.0f} บัญชี<extra></extra>",
            ))

            # Line: cumulative (ขวา) — เส้นทึบสีแดง
            fig_web.add_trace(go.Scatter(
                x=wf["month_label"],
                y=wf["cumulative_total"],
                name="สมาชิกสะสม (บัญชี)",
                mode="lines+markers+text",
                line=dict(color="#D32F2F", width=3),
                marker=dict(size=9, color="#D32F2F"),
                text=wf["cumulative_total"].apply(lambda x: f"{x:,.0f}"),
                textposition="top center",
                textfont=dict(size=9, color="#D32F2F"),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>สะสม: %{y:,.0f} บัญชี<extra></extra>",
            ))

            # Growth badges บนยอดแท่ง (สีเขียว/แดง) — ใช้ได้เพราะใหม่/เดือนขึ้นลงได้
            for _, row in wf.iterrows():
                g = row["growth_pct"]
                if pd.isna(g):
                    continue
                if g > 0:
                    arrow, bg, fg, bd = "▲", "#C8E6C9", "#1B5E20", "#66BB6A"
                elif g < 0:
                    arrow, bg, fg, bd = "▼", "#FFCDD2", "#B71C1C", "#E57373"
                else:
                    arrow, bg, fg, bd = "●", "#E0E0E0", "#424242", "#BDBDBD"
                fig_web.add_annotation(
                    x=row["month_label"],
                    y=row["new_registrations"] * 0.5,
                    text=f"<b>{arrow} {g:+.1f}%</b>",
                    showarrow=False,
                    bgcolor=bg,
                    bordercolor=bd,
                    borderwidth=1,
                    borderpad=2,
                    font=dict(size=8, color=fg),
                    xanchor="center",
                    yanchor="middle",
                )

            fig_web.update_layout(
                title="จำนวนการสมัครสมาชิกใหม่บนเว็บไซต์ thaieasypass (รายเดือนและสะสม)",
                height=520,
                yaxis=dict(
                    title="สมัครใหม่รายเดือน (บัญชี)",
                    gridcolor="#E0E6ED",
                    tickformat=",.0f",
                    side="left",
                ),
                yaxis2=dict(
                    title="สมัครสะสม (บัญชี)",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickformat=",.0f",
                ),
                xaxis=dict(title="เดือน", tickangle=-45),
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
                plot_bgcolor="#FAFBFC",
                margin=dict(t=80, b=100, l=80, r=80),
                bargap=0.4,
            )
            st.plotly_chart(fig_web, use_container_width=True)

            # ---------- ตารางรายเดือน ----------
            st.markdown(sub_section_title("📋 ตารางรายละเอียด"), unsafe_allow_html=True)
            wd = website.copy()
            wd["new_fmt"] = wd["new_registrations"].apply(lambda x: f"{x:,.0f}")
            wd["cum_fmt"] = wd["cumulative_total"].apply(lambda x: f"{x:,.0f}")
            wd["chg"] = wd["new_registrations"].diff().fillna(0).apply(
                lambda x: f"{x:+,.0f}" if x != 0 else "-"
            )
            wd["chg_pct"] = wd["new_registrations"].pct_change().fillna(0).apply(
                lambda x: f"{x:+.1f}%" if x != 0 else "-"
            )
            wd = wd[["month_label", "new_fmt", "chg", "chg_pct", "cum_fmt"]]
            wd.columns = ["เดือน", "สมัครใหม่ (บัญชี)", "Δ", "%Δ", "สะสม (บัญชี)"]
            st.dataframe(wd, use_container_width=True, hide_index=True)

# =============================================================================

            st.markdown(sub_section_title("💡 Interpretation — สถิติเว็บไซต์"), unsafe_allow_html=True)
            w_chg_val = pct_change(w_new_curr, w_new_prev) if len(website) > 1 else None
            bullets = [
                f"เดือนล่าสุดมีสมาชิกสมัครใหม่ <b>{w_new_curr:,.0f} บัญชี</b>" + (f" เปลี่ยนแปลง {w_chg_val:+.1f}% จากเดือนก่อน" if w_chg_val is not None else ""),
                f"ยอดสมาชิกสะสมล่าสุด <b>{w_cum_curr:,.0f} บัญชี</b> เพิ่มขึ้น {w_cum_growth:+.1f}% จากจุดเริ่มต้นของช่วงข้อมูลที่ {w_cum_first:,.0f} บัญชี",
                f"ค่าเฉลี่ยการสมัครใหม่ {w_new_avg:,.0f} บัญชี/เดือน และยอดสูงสุดที่ {w_new_max:,.0f} บัญชี (เดือน {w_new_max_month})",
                f"ยอดสมัครใหม่รวมทั้งช่วง {len(website)} เดือน = <b>{w_new_total:,.0f} บัญชี</b>",
                "ตัวเลขนี้สะท้อนจำนวนบัญชีที่สมัคร ไม่ได้เท่ากับจำนวนผู้ใช้ที่ Active หรือจำนวนธุรกรรม",
            ]
            st.markdown(html_interpretation("สถิติเว็บไซต์", bullets), unsafe_allow_html=True)

# TAB: 💳 สถานะบัตรในระบบ
# =============================================================================
if tab_status is not None:
    with tab_status:
        st.markdown(section_title("💳 7. สถานะบัตรอัตโนมัติ Easy Pass ทั้งหมดในระบบ CCH", "หน้า 18"), unsafe_allow_html=True)
        if n_error == 0 and not card_status.empty:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(kpi_tile("✅ บัตร Active", f"{card_status['active_cards'].iloc[-1]:,.0f}", "ใช้งานได้", color="green"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_tile("⚠️ ถูกระงับ", f"{card_status['suspended_cards'].iloc[-1]:,.0f}", "Suspended", color="orange"), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi_tile("💸 เงินเหลือต่ำ", f"{card_status['low_balance_cards'].iloc[-1]:,.0f}", "Low Balance", color="orange"), unsafe_allow_html=True)
            with c4:
                st.markdown(kpi_tile("🆘 บัตรหาย", f"{card_status['lost_count'].iloc[-1]:,.0f}", f"มูลค่า {card_status['lost_value_baht'].iloc[-1]/1e6:,.1f} ลบ.", color="red"), unsafe_allow_html=True)
            st.markdown("---")

            fig = px.bar(card_status, x="month_label", y=["suspended_cards", "low_balance_cards"],
                          barmode="group", title="แนวโน้มบัตรไม่พร้อมใช้งาน")
            fig.update_layout(height=430, yaxis_title="บัตร", legend=dict(orientation="h", y=1.12),
                               plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

        if not card_detail.empty:
            st.markdown(sub_section_title("📊 7.1 + 7.2 รายละเอียดสถานะบัตร (BEM + EXAT)", "หน้า 18"), unsafe_allow_html=True)
            col_sd1, col_sd2 = st.columns([1.3, 1])
            with col_sd1:
                cd_disp = card_detail.copy()
                for c in ["bem_count", "exat_count", "total_count"]:
                    if c in cd_disp.columns:
                        cd_disp[c] = cd_disp[c].apply(lambda x: f"{x:,.0f}")
                if "percent" in cd_disp.columns:
                    cd_disp["percent"] = cd_disp["percent"].apply(lambda x: f"{x:.2f}%")
                st.dataframe(cd_disp, use_container_width=True, hide_index=True)
            with col_sd2:
                cch = card_detail[~card_detail["status_name"].str.contains("รวม", na=False)].copy()
                if not cch.empty:
                    fig_cd = px.bar(cch, x="status_name", y="total_count", color="status_group", text="total_count")
                    fig_cd.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_cd.update_layout(xaxis_tickangle=-30, height=430, yaxis_title="บัตร",
                                          legend=dict(orientation="h", y=-0.3))
                    st.plotly_chart(fig_cd, use_container_width=True)
            st.markdown("---")

        if not inactive_bal.empty:
            st.markdown(sub_section_title("💤 7.3 เงินคงเหลือในบัตรพร้อมใช้งานไม่เคลื่อนไหวเกิน 2 ปี", "หน้า 18"), unsafe_allow_html=True)
            ib_total = inactive_bal[inactive_bal["amount_range"] == "รวมทั้งหมด"]
            if not ib_total.empty:
                tot_cards = ib_total["card_count"].iloc[0]
                tot_amt = ib_total["amount_baht"].iloc[0]
                i1, i2 = st.columns(2)
                with i1:
                    st.markdown(kpi_tile("💳 จำนวนบัตร", f"{tot_cards:,.0f}", "ไม่เคลื่อนไหว >2 ปี", color="orange"), unsafe_allow_html=True)
                with i2:
                    st.markdown(kpi_tile("💰 มูลค่ารวม", f"{tot_amt/1e6:,.1f} ลบ.", "เงินคงเหลือ", color="red"), unsafe_allow_html=True)
                st.markdown("---")

            col_ib1, col_ib2 = st.columns([1.1, 1])
            with col_ib1:
                ib_disp = inactive_bal.copy()
                ib_disp["card_count"] = ib_disp["card_count"].apply(lambda x: f"{x:,.0f}")
                ib_disp["amount_baht"] = ib_disp["amount_baht"].apply(lambda x: f"{x:,.2f}")
                ib_disp.columns = ["ช่วงเงินคงเหลือ", "จำนวนบัตร", "มูลค่า (บาท)"]
                st.dataframe(ib_disp, use_container_width=True, hide_index=True)
            with col_ib2:
                ib = inactive_bal[inactive_bal["amount_range"] != "รวมทั้งหมด"].copy()
                if not ib.empty:
                    fig_ib = px.bar(ib, x="amount_range", y="card_count", text="card_count",
                                     color="card_count", color_continuous_scale="Reds")
                    fig_ib.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_ib.update_layout(xaxis_tickangle=-30, coloraxis_showscale=False,
                                          height=430, yaxis_title="จำนวนบัตร")
                    st.plotly_chart(fig_ib, use_container_width=True)

# =============================================================================

            st.markdown(sub_section_title("💡 Interpretation — สถานะบัตรในระบบ"), unsafe_allow_html=True)
            active_now = card_status["active_cards"].iloc[-1]
            suspended_now = card_status["suspended_cards"].iloc[-1]
            low_now = card_status["low_balance_cards"].iloc[-1]
            lost_now = card_status["lost_count"].iloc[-1]
            total_status = active_now + suspended_now + low_now + lost_now
            bullets = [
                f"บัตร Active มี {active_now:,.0f} ใบ ขณะที่ Suspended {suspended_now:,.0f} ใบ, Low Balance {low_now:,.0f} ใบ และ Lost {lost_now:,.0f} ใบในเดือนล่าสุด",
                f"หากใช้ผลรวมของสถานะที่รายงานเป็นฐานเดียวกัน Active คิดเป็น {safe_pct(active_now,total_status):.1f}% ของสถานะที่นำมาคำนวณ",
                f"Low Balance คิดเป็น {safe_pct(low_now,total_status):.1f}% และ Lost คิดเป็น {safe_pct(lost_now,total_status):.1f}% ของผลรวมดังกล่าว",
                "สถานะแต่ละประเภทอาจมีความสัมพันธ์กันตามนิยามของระบบ จึงไม่ควรถือว่าผลรวมทุกสถานะเท่ากับจำนวนบัตรที่ไม่ซ้ำกันโดยอัตโนมัติ",
            ]
            if not inactive_bal.empty and not ib_total.empty:
                bullets.append(f"บัตรพร้อมใช้งานที่ไม่เคลื่อนไหวเกิน 2 ปีมี {tot_cards:,.0f} ใบ มูลค่า {tot_amt/1e6:,.1f} ล้านบาทตามข้อมูลที่รายงาน")
            st.markdown(html_interpretation("สถานะบัตรในระบบ", bullets,
                "สัดส่วนข้างต้นใช้เพื่อช่วยอ่านโครงสร้างข้อมูลเท่านั้น ไม่ได้ยืนยันว่าแต่ละสถานะไม่ซ้อนทับกัน"), unsafe_allow_html=True)

# TAB: ☎️ เรื่องร้องเรียน & CS
# =============================================================================
if tab_cs is not None:
    with tab_cs:
        st.markdown(section_title("☎️ 8-9. สรุปสถิติการรับเรื่องที่ศูนย์บริการลูกค้าบัตรอัตโนมัติ (Easy Pass Customer Service)", "หน้า 20"), unsafe_allow_html=True)

        if n_error == 0 and not cs.empty:
            cs_curr = cs["total_cases"].iloc[-1]
            cs_prev = cs["total_cases"].iloc[-2]
            cs_total_fy = cs["total_cases"].sum()
            cs_avg = cs["total_cases"].mean()

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(kpi_tile("📅 เดือนนี้", f"{cs_curr:,.0f}", "เรื่อง", color="blue"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_tile("📈 MoM", f"{pct_change(cs_curr, cs_prev):+.1f}%", "เทียบเดือนก่อน", color="orange" if cs_curr >= cs_prev else "green"), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi_tile("📊 สะสมปีงบ 69", f"{cs_total_fy:,.0f}", f"เรื่อง (ข้อมูลสะสมถึง {LATEST_MONTH})", color="purple"), unsafe_allow_html=True)
            with c4:
                st.markdown(kpi_tile("📉 เฉลี่ย/เดือน", f"{cs_avg:,.0f}", "เรื่อง/เดือน", color="teal"), unsafe_allow_html=True)
            st.markdown("---")

        if n_error == 0 and not cs.empty:
            fig = px.line(cs, x="month_label", y="total_cases", markers=True,
                          title="แนวโน้มเรื่องร้องเรียนรายเดือน")
            fig.update_traces(line_color="#0B5ED7", line_width=3, marker=dict(size=9))
            fig.update_layout(height=430, yaxis_title="เรื่อง", plot_bgcolor="#FAFBFC")
            st.plotly_chart(fig, use_container_width=True)

            cv = [c for c in cs.columns if c not in ("month", "month_label", "total_cases")]
            if cv:
                st.markdown(sub_section_title("📊 แยกประเภทเรื่องร้องเรียน"), unsafe_allow_html=True)
                fig_cs = px.bar(cs, x="month_label", y=cv, barmode="stack",
                                 title="แยกประเภทเรื่องร้องเรียน")
                fig_cs.update_layout(height=430, yaxis_title="เรื่อง", legend=dict(orientation="h", y=-0.2),
                                      plot_bgcolor="#FAFBFC")
                st.plotly_chart(fig_cs, use_container_width=True)

                latest_cv = cs.iloc[-1][cv].astype(float)
                latest_cv = latest_cv[latest_cv > 0]
                if not latest_cv.empty:
                    pie_cs = pd.DataFrame({"ประเภท": latest_cv.index, "จำนวน": latest_cv.values})
                    fig_pie_cs = px.pie(pie_cs, names="ประเภท", values="จำนวน", hole=0.4,
                                         title=f"สัดส่วนประเภทเรื่องร้องเรียน เดือน {cs['month_label'].iloc[-1]}")
                    fig_pie_cs.update_traces(textinfo="label+percent", textfont_size=10)
                    fig_pie_cs.update_layout(height=480)
                    st.plotly_chart(fig_pie_cs, use_container_width=True)
            else:
                st.markdown("""
                <div class="info-banner">
                    ℹ️ ข้อมูลที่มีในระบบเป็น <b>ยอดรวม</b> ของเรื่องร้องเรียนเท่านั้น
                    หากต้องการรายละเอียดแยกประเภท (Check bill, Easy Pass/M-Flow, ค่าธรรมเนียมบัตร, อื่นๆ)
                    กรุณาเพิ่มคอลัมน์ประเภทในไฟล์ <code>14_customer_service.csv</code>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(sub_section_title("📋 ตารางแนวโน้มรายเดือน"), unsafe_allow_html=True)
            csd = cs.copy()
            csd["total_cases"] = csd["total_cases"].apply(lambda x: f"{x:,.0f}")
            csd["chg"] = cs["total_cases"].diff().fillna(0).apply(lambda x: f"{x:+,.0f}" if x != 0 else "-")
            show_cols = ["month_label", "total_cases", "chg"] + cv
            csd = csd[[c for c in show_cols if c in csd.columns]]
            st.dataframe(csd, use_container_width=True, hide_index=True)

# =============================================================================

            st.markdown(sub_section_title("💡 Interpretation — เรื่องร้องเรียน & Customer Service"), unsafe_allow_html=True)
            cs_chg_latest = pct_change(cs_curr, cs_prev) if len(cs) > 1 else None
            bullets = [
                f"เดือนล่าสุดมีเรื่องร้องเรียน {cs_curr:,.0f} เรื่อง" + (f" เปลี่ยนแปลง {cs_chg_latest:+.1f}% จากเดือนก่อน" if cs_chg_latest is not None else ""),
                f"ยอดสะสมของช่วงข้อมูล {cs_total_fy:,.0f} เรื่อง และค่าเฉลี่ย {cs_avg:,.0f} เรื่อง/เดือน",
                f"เดือนล่าสุดอยู่ {'สูงกว่า' if cs_curr > cs_avg else 'ต่ำกว่าหรือเท่ากับ'} ค่าเฉลี่ยของช่วงข้อมูล",
                "หากมีเพียงยอดรวมรายเดือน ยังสามารถตีความระดับและแนวโน้มของภาระงานได้ แต่ยังไม่สามารถระบุประเภทปัญหาหรือสาเหตุของการเพิ่มลดได้",
            ]
            st.markdown(html_interpretation("เรื่องร้องเรียน & Customer Service", bullets), unsafe_allow_html=True)

# TAB: 📊 ยอดสะสมปีงบ 2569
# =============================================================================
with tab_annual:
    st.markdown(section_title("📊 สรุปยอดสะสมปีงบประมาณ 2569"), unsafe_allow_html=True)
    if n_error == 0 and not annual_summary.empty:
        for cat in annual_summary["category"].unique():
            st.markdown(sub_section_title(f"📌 {cat}"), unsafe_allow_html=True)
            cat_df = annual_summary[annual_summary["category"] == cat]
            cols = st.columns(min(len(cat_df), 4))
            for i, (_, row) in enumerate(cat_df.iterrows()):
                col = cols[i % len(cols)]
                v = row["value"]; u = row["unit"]
                if u == "บาท" and v >= 1e9: dv = f"{v/1e9:,.2f} พันล้านบาท"
                elif u == "บาท": dv = f"{v/1e6:,.1f} ล้านบาท"
                else: dv = f"{v:,.0f} {u}"
                col.metric(row["metric_th"], dv)

        st.markdown("---")
        st.markdown(sub_section_title("📋 ตารางข้อมูลทั้งหมด"), unsafe_allow_html=True)
        ad = annual_summary.copy()
        ad["value"] = ad["value"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(ad, use_container_width=True, hide_index=True)

# =============================================================================

        st.markdown(sub_section_title("💡 Interpretation — ยอดสะสมปีงบประมาณ"), unsafe_allow_html=True)
        if not annual_summary.empty:
            bullets = [
                f"ชุดข้อมูลยอดสะสมปีงบประมาณประกอบด้วย {len(annual_summary):,} ตัวชี้วัด แบ่งเป็น {annual_summary['category'].nunique():,} หมวดข้อมูล",
                "ค่าที่แสดงเป็นยอดสะสมหรือค่ารายงานตามนิยามของแต่ละ metric จึงไม่ควรนำทุกตัวชี้วัดมารวมเป็นดัชนีเดียว",
                "การตีความควรพิจารณาหน่วยและช่วงเวลาที่ครอบคลุมของแต่ละ metric ก่อนเปรียบเทียบข้ามหมวด"
            ]
            st.markdown(html_interpretation("ยอดสะสมปีงบประมาณ", bullets), unsafe_allow_html=True)

# TAB: 🚨 ศูนย์แจ้งเตือน
# =============================================================================
with tab_warning:
    st.markdown(section_title("🚨 ศูนย์แจ้งเตือน (Early Warning Center)"), unsafe_allow_html=True)
    if alerts_df.empty:
        st.warning("ไม่สามารถคำนวณได้")
    else:
        cmap = {
            "CRITICAL": "background-color:#F8D7DA",
            "WARNING":  "background-color:#FFF3CD",
            "NORMAL":   "background-color:#D4EDDA",
            "N/A":      "background-color:#ECEFF1",
        }
        icon_map = {
            "CRITICAL": "🔴", "WARNING": "🟠",
            "NORMAL": "🟢", "N/A": "⚪",
        }
        label_map = {
            "CRITICAL": "วิกฤต", "WARNING": "เฝ้าระวัง",
            "NORMAL": "ปกติ", "N/A": "ไม่มีข้อมูล",
        }

        # นับ N/A และแสดง banner
        if n_na > 0:
            st.markdown(
                f'<div class="info-banner">⚪ มี <b>{n_na} รายการ</b> '
                f'ที่ยังไม่มีข้อมูลเพียงพอ (ต้องมี ≥13 เดือนสำหรับ YoY หรือ ≥4 งวดสำหรับ Trend) '
                f'จึงไม่ถูกนำมาคำนวณ Health Score</div>',
                unsafe_allow_html=True,
            )

        # ให้ผู้ใช้เลือกกรอง
        filter_group = st.multiselect(
            "กรองตามกลุ่มเกณฑ์:",
            options=["A", "B", "C", "D"],
            default=["A", "B", "C", "D"],
            format_func=lambda x: {
                "A": "A · Fixed", "B": "B · YoY",
                "C": "C · Trend", "D": "D · Ratio",
            }.get(x, x),
        )
        
        view_df = alerts_df[alerts_df["กลุ่ม"].isin(filter_group)].copy() if "กลุ่ม" in alerts_df.columns else alerts_df.copy()

        # ---------- Helper: แสดง "ค่าอ้างอิง" พร้อม icon ตามกลุ่มเกณฑ์ ----------
        def _ref_display(grp, ref_val):
            """
            นำ icon นำหน้า ค่าอ้างอิง ตามกลุ่มเกณฑ์:
              A Fixed   → 🎯 เกณฑ์คงที่ (absolute threshold)
              B YoY     → 📅 เทียบปีก่อน (Year-over-Year)
              C Trend   → 📊 เฉลี่ย 3 งวดก่อน (rolling avg)
              D Ratio   → 📐 เกณฑ์อัตราส่วน (ratio threshold)
            """
            grp_icon = {"A": "🎯", "B": "📅", "C": "📊", "D": "📐"}.get(grp, "•")
            ref_str = str(ref_val).strip() if ref_val is not None else ""
            if ref_str in ("", "—", "nan", "None"):
                return {
                    "A": "🎯 เกณฑ์คงที่",
                    "B": "📅 ยังไม่มีข้อมูลปีก่อน",
                    "C": "📊 ยังไม่มีข้อมูลย้อนหลัง",
                    "D": "📐 เกณฑ์คงที่",
                }.get(grp, "—")
            return f"{grp_icon} {ref_val}"

        da = view_df.copy()
        # ✅ เปลี่ยนชื่อคอลัมน์ + prepend icon
        da["เดือนก่อน"] = da.apply(
            lambda r: _ref_display(r.get("กลุ่ม", ""), r.get("เดือนก่อน", "")),
            axis=1,
        )
        da = da.rename(columns={"เดือนก่อน": "ค่าอ้างอิง"})
        da["สถานะ"] = da["สถานะ"].apply(lambda s: f"{icon_map.get(s,'⚪')} {label_map.get(s, s)}")
        
        st.dataframe(
            da.style.apply(
                lambda r: [cmap.get(view_df.loc[r.name, "สถานะ"], "")] * len(r),
                axis=1,
            ),
            use_container_width=True, hide_index=True,
        )
        
        st.caption(
            "💡 **คำอธิบายคอลัมน์ \"ค่าอ้างอิง\":** "
            "🎯 เกณฑ์คงที่ (A/D) · "
            "📅 เทียบปีก่อน (B) · "
            "📊 เฉลี่ย 3 งวดก่อน (C)"
        )

        for _, row in view_df.iterrows():
            s = row["สถานะ"]
            icon = icon_map.get(s, "⚪")
            label = label_map.get(s, s)
            ref_disp = _ref_display(row.get("กลุ่ม", ""), row.get("เดือนก่อน", ""))
            with st.expander(f"{icon} {row['หัวข้อ']} — {label}"):
                st.write(
                    f"**กลุ่มเกณฑ์:** {row.get('กลุ่ม','-')} &nbsp;|&nbsp; "
                    f"**ค่าล่าสุด:** {row['ค่าล่าสุด']} &nbsp;|&nbsp; "
                    f"**ค่าอ้างอิง:** {ref_disp} &nbsp;|&nbsp; "
                    f"**เปลี่ยนแปลง:** {row['เปลี่ยนแปลง']}"
                )
                st.info(row["คำแนะนำ"])

# =============================================================================

        st.markdown(sub_section_title("💡 Interpretation — ศูนย์แจ้งเตือน"), unsafe_allow_html=True)
        if not alerts_df.empty:
            bullets = [
                f"ระบบประเมินจาก {len(alerts_df):,} ตัวชี้วัดที่มี threshold โดยปัจจุบันอยู่ในระดับปกติ {n_normal:,} รายการ, เฝ้าระวัง {n_warning:,} รายการ และวิกฤต {n_critical:,} รายการ",
                "สถานะ Early Warning เป็นการจัดระดับตาม threshold ที่ตั้งไว้ ไม่ใช่ข้อพิสูจน์ว่ามีปัญหาเชิงสาเหตุ",
                "การอ่านผลที่น่าเชื่อถือควรดูค่าดิบ การเปลี่ยนแปลง MoM และบริบทของตัวหาร/ฐานข้อมูลของแต่ละตัวชี้วัดร่วมกัน"
            ]
            st.markdown(html_interpretation("ศูนย์แจ้งเตือน", bullets), unsafe_allow_html=True)

# TAB: 📑 ออกรายงาน PDF
# =============================================================================
if can_export and tab_export is not None:
    with tab_export:
        st.subheader("📑 ออกรายงาน PDF")
        default_opts = {"opt_summary": True, "opt_warning": True, "opt_reg": True, "opt_inv": True,
                        "opt_traffic": True, "opt_anomaly": True, "opt_emv": True, "opt_motorway": True,
                        "opt_topup": True, "opt_web": True, "opt_status": True, "opt_cs": True, "opt_annual": True}
        for k, v in default_opts.items():
            if k not in st.session_state: st.session_state[k] = v

        col_s1, col_s2, _ = st.columns([1, 1, 3])
        with col_s1:
            if st.button("✅ เลือกทั้งหมด", use_container_width=True):
                for k in default_opts: st.session_state[k] = True
                st.rerun()
        with col_s2:
            if st.button("⬜ ยกเลิกทั้งหมด", use_container_width=True):
                for k in default_opts: st.session_state[k] = False
                st.rerun()

        col_a, col_b = st.columns(2)
        with col_a:
            opt_summary = st.checkbox("📋 1. บทสรุปผู้บริหาร", key="opt_summary")
            opt_warning = st.checkbox("🚨 2. Early Warning", key="opt_warning")
            opt_reg = st.checkbox("🪪 3. ยอดสมัครบัตร", key="opt_reg")
            opt_inv = st.checkbox("📦 4. ยอดคงเหลือบัตร", key="opt_inv")
            opt_traffic = st.checkbox("🚦 5. ปริมาณจราจร / ETC", key="opt_traffic")
            opt_anomaly = st.checkbox("⚠️ 6. เหตุการณ์ไม้กั้น", key="opt_anomaly")
            opt_emv = st.checkbox("💳 7. ปริมาณ EMV", key="opt_emv")
        with col_b:
            opt_motorway = st.checkbox("🛣️ 8. มอเตอร์เวย์ / โทลล์เวย์", key="opt_motorway")
            opt_topup = st.checkbox("💰 9. ยอดเติมเงิน", key="opt_topup")
            opt_web = st.checkbox("🌐 10. เว็บไซต์", key="opt_web")
            opt_status = st.checkbox("💳 11. สถานะบัตร", key="opt_status")
            opt_cs = st.checkbox("☎️ 12. ศูนย์บริการลูกค้า", key="opt_cs")
            opt_annual = st.checkbox("📊 13. ยอดสะสมปีงบ", key="opt_annual")

        submit_export = st.button("🔄 สร้างรายงาน PDF", type="primary", use_container_width=True)
        if submit_export:
            if n_error > 0:
                st.error(f"⚠️ มีข้อมูลผิดพลาด {n_error} ไฟล์")
            else:
                options = {"summary": opt_summary, "warning": opt_warning, "reg": opt_reg, "inv": opt_inv,
                           "traffic": opt_traffic, "anomaly": opt_anomaly, "emv": opt_emv,
                           "motorway": opt_motorway, "topup": opt_topup, "web": opt_web,
                           "status": opt_status, "cs": opt_cs, "annual": opt_annual}
                if not any(options.values()):
                    st.warning("⚠️ กรุณาเลือกอย่างน้อย 1 หัวข้อ")
                else:
                    with st.spinner("🖨️ กำลังสร้างรายงาน PDF..."):
                        try:
                            data_bundle = {"reg": reg, "inv": inv, "etc": etc, "route": route,
                                            "anomaly": anomaly, "emv": emv, "motorway": motorway,
                                            "topup_total": topup_total, "topup_edc": topup_edc,
                                            "topup_ext": topup_ext, "topup_digital": topup_digital,
                                            "website": website, "card_status": card_status, "cs": cs,
                                            "traffic_4w": traffic_4w, "route_detail": route_detail,
                                            "tollway_detail": tollway_detail, "annual_summary": annual_summary,
                                            "reg_by_route": reg_by_route, "inv_by_route": inv_by_route,
                                            "traffic_full": traffic_full, "mpass_detail": mpass_detail,
                                            "topup_channel": topup_channel, "card_detail": card_detail,
                                            "inactive_bal": inactive_bal, "anomaly_by_route": anomaly_by_route,
                                            "anomaly_cause": anomaly_cause}
                            pdf_bytes = generate_pdf_report(latest_month=LATEST_MONTH, username=user["name"],
                                                             data=data_bundle, alerts_df=alerts_df, options=options)
                            st.success(f"✅ สร้างสำเร็จ ({len(pdf_bytes)/1024:.1f} KB)")
                            st.download_button("⬇️ ดาวน์โหลด PDF", data=pdf_bytes,
                                                file_name=f"EASY_PASS_Executive_Report_{LATEST_MONTH.replace(' ', '_')}.pdf",
                                                mime="application/pdf", use_container_width=True, type="primary")
                            append_audit(user["name"], "Export รายงาน PDF",
                                          {"เดือน": LATEST_MONTH, "หัวข้อ": [k for k, v in options.items() if v]})
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
                            st.exception(e)

st.markdown("---")
st.caption("การทางพิเศษแห่งประเทศไทย (กทพ.) | ระบบสารสนเทศเพื่อการบริหารจัดการ ปีงบประมาณ 2569")