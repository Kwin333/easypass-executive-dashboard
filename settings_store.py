"""
settings_store.py — ชั้นจัดเก็บค่าตั้งค่าถาวรของระบบ (Persistence Layer)
Dashboard EASY PASS | การทางพิเศษแห่งประเทศไทย (กทพ.)

หน้าที่:
  1. จัดเก็บ/อ่านค่าเกณฑ์ Early Warning แบบถาวรบนดิสก์ (รอดจากการ Log out และรีสตาร์ตระบบ)
  2. จัดเก็บไฟล์ข้อมูลที่ผู้ดูแลระบบอัปโหลด และจดจำไฟล์ที่ใช้งานล่าสุด
  3. บันทึกประวัติการเปลี่ยนแปลง (Audit Log) เพื่อการตรวจสอบย้อนหลัง
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# โครงสร้างไดเรกทอรีของระบบ
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = BASE_DIR / "config"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
SETTINGS_FILE = CONFIG_DIR / "app_settings.json"
AUDIT_FILE = CONFIG_DIR / "settings_audit_log.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# ค่าเริ่มต้นมาตรฐานของระบบ (ใช้เฉพาะครั้งแรกสุดที่ยังไม่เคยมีการตั้งค่า)
# ปรับคีย์และตัวเลขให้ตรงกับเกณฑ์จริงที่ใช้ใน app.py ของคุณ
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "thresholds": {
        # เกณฑ์สต็อกอุปกรณ์ (หน่วย: ใบ) - ต่ำกว่าเกณฑ์ = เตือน/วิกฤต
        "obu_warning": 180000,
        "obu_critical": 150000,
        "smartcard_warning": 150000,
        "smartcard_critical": 120000,

        # เกณฑ์การเปลี่ยนแปลงเชิงร้อยละ (หน่วย: %) - ติดลบมากกว่าเกณฑ์ = เตือน/วิกฤต
        "new_member_warning_pct": -10.0,
        "new_member_critical_pct": -20.0,
        "revenue_warning_pct": -5.0,
        "revenue_critical_pct": -10.0,
        "anomaly_warning_pct": 10.0,
        "anomaly_critical_pct": 20.0,
        "lostcard_warning_pct": 10.0,
        "lostcard_critical_pct": 20.0,
        "complaint_warning_pct": 10.0,
        "complaint_critical_pct": 20.0,
        "etc_ratio_warning_pp": -0.5,
        "etc_ratio_critical_pp": -1.0,
    },
    "active_data_file": None,       # เส้นทางไฟล์ข้อมูลที่ใช้งานอยู่ปัจจุบัน
    "active_data_label": None,      # ชื่อไฟล์ต้นฉบับที่ผู้ใช้อัปโหลด
    "uploaded_at": None,
    "uploaded_by": None,
    "updated_at": None,
    "updated_by": None,
    "schema_version": 1,
}


# ---------------------------------------------------------------------------
# ฟังก์ชันภายใน
# ---------------------------------------------------------------------------
def _deep_merge(base: dict, override: dict) -> dict:
    """รวมค่าที่อ่านจากไฟล์เข้ากับค่าเริ่มต้น เพื่อรองรับการเพิ่มคีย์ใหม่ในอนาคต"""
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _atomic_write_json(path: Path, payload: dict) -> None:
    """เขียนไฟล์แบบปลอดภัย ป้องกันไฟล์เสียหายหากระบบดับกลางคัน"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# ฟังก์ชันหลักสำหรับเรียกใช้จาก app.py
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    """อ่านค่าตั้งค่าล่าสุดจากดิสก์ หากยังไม่มีไฟล์จะสร้างจากค่าเริ่มต้นให้อัตโนมัติ"""
    if not SETTINGS_FILE.exists():
        _atomic_write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            stored = json.load(fh)
        return _deep_merge(DEFAULT_SETTINGS, stored)
    except (json.JSONDecodeError, OSError):
        # ไฟล์เสียหาย: สำรองไฟล์เดิมไว้ตรวจสอบ แล้วคืนค่าเริ่มต้น
        if SETTINGS_FILE.exists():
            shutil.copy2(SETTINGS_FILE, SETTINGS_FILE.with_suffix(".corrupted.bak"))
        _atomic_write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict, username: str = "system") -> dict:
    """บันทึกค่าตั้งค่าทั้งชุดลงดิสก์"""
    payload = _deep_merge(DEFAULT_SETTINGS, settings)
    payload["updated_at"] = _now()
    payload["updated_by"] = username
    _atomic_write_json(SETTINGS_FILE, payload)
    return payload


def update_thresholds(new_thresholds: dict, username: str = "system") -> dict:
    """ปรับเฉพาะค่าเกณฑ์ Early Warning แล้วบันทึกถาวรพร้อมลง Audit Log"""
    current = load_settings()
    old = dict(current["thresholds"])
    current["thresholds"] = _deep_merge(current["thresholds"], new_thresholds)
    saved = save_settings(current, username)

    changed = {
        k: {"from": old.get(k), "to": saved["thresholds"].get(k)}
        for k in saved["thresholds"]
        if old.get(k) != saved["thresholds"].get(k)
    }
    if changed:
        append_audit(username, "ปรับค่าเกณฑ์ Early Warning", changed)
    return saved


def reset_thresholds_to_default(username: str = "system") -> dict:
    """คืนค่าเกณฑ์กลับสู่ค่ามาตรฐานของระบบ"""
    current = load_settings()
    current["thresholds"] = dict(DEFAULT_SETTINGS["thresholds"])
    saved = save_settings(current, username)
    append_audit(username, "คืนค่าเกณฑ์กลับสู่ค่ามาตรฐาน", {})
    return saved


def save_uploaded_file(uploaded_file, username: str = "system") -> dict:
    """
    บันทึกไฟล์ข้อมูลที่อัปโหลดลงดิสก์จริง และตั้งเป็นไฟล์ใช้งานปัจจุบัน
    รับอ็อบเจกต์จาก st.file_uploader
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    target = UPLOAD_DIR / f"{stamp}__{safe_name}"

    with open(target, "wb") as fh:
        fh.write(uploaded_file.getbuffer())

    settings = load_settings()
    previous = settings.get("active_data_label")
    settings["active_data_file"] = str(target)
    settings["active_data_label"] = uploaded_file.name
    settings["uploaded_at"] = _now()
    settings["uploaded_by"] = username
    saved = save_settings(settings, username)

    append_audit(
        username,
        "อัปโหลดไฟล์ข้อมูลชุดใหม่",
        {"ไฟล์เดิม": previous, "ไฟล์ใหม่": uploaded_file.name, "ที่จัดเก็บ": str(target)},
    )
    return saved


def get_active_data_path(fallback: str | None = None) -> str | None:
    """
    คืนเส้นทางไฟล์ข้อมูลที่ใช้งานอยู่
    หากยังไม่เคยอัปโหลด หรือไฟล์ถูกลบไป จะคืนค่าไฟล์ตั้งต้น (fallback) แทน
    """
    settings = load_settings()
    path = settings.get("active_data_file")
    if path and Path(path).exists():
        return path
    return fallback


def file_signature(path) -> str:
    """ลายเซ็นไฟล์ (ขนาด + เวลาแก้ไขล่าสุด) ใช้เป็นคีย์ล้างแคชเมื่อไฟล์เปลี่ยน"""
    if not path:
        return "none"
    p = Path(path)
    if not p.exists():
        return "missing"
    stat = p.stat()
    return f"{p.name}|{stat.st_size}|{int(stat.st_mtime)}"


def list_uploaded_files() -> list:
    """รายการไฟล์ข้อมูลทั้งหมดที่เคยอัปโหลด เรียงจากใหม่ไปเก่า"""
    files = sorted(UPLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "path": str(p),
            "name": p.name,
            "size_kb": round(p.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        }
        for p in files if p.is_file()
    ]


def set_active_data_file(path: str, username: str = "system") -> dict:
    """เลือกไฟล์ที่เคยอัปโหลดไว้แล้วกลับมาใช้งานใหม่ (ย้อนกลับไปใช้ข้อมูลเดือนก่อนหน้า)"""
    settings = load_settings()
    settings["active_data_file"] = path
    settings["active_data_label"] = Path(path).name
    saved = save_settings(settings, username)
    append_audit(username, "เปลี่ยนไฟล์ข้อมูลที่ใช้งาน", {"ไฟล์ที่เลือก": Path(path).name})
    return saved


# ---------------------------------------------------------------------------
# ระบบบันทึกประวัติการเปลี่ยนแปลง (Audit Log)
# ---------------------------------------------------------------------------
def append_audit(username: str, action: str, detail: dict) -> None:
    logs = get_audit_log()
    logs.insert(0, {
        "timestamp": _now(),
        "user": username,
        "action": action,
        "detail": detail,
    })
    _atomic_write_json(AUDIT_FILE, {"logs": logs[:500]})  # เก็บย้อนหลัง 500 รายการ


def get_audit_log() -> list:
    if not AUDIT_FILE.exists():
        return []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh).get("logs", [])
    except (json.JSONDecodeError, OSError):
        return []