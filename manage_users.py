"""
manage_users.py — เครื่องมือตั้ง/รีเซ็ตรหัสผ่านผู้ใช้งานทั้งหมด
รันครั้งเดียวเพื่อสร้างไฟล์ config/users.yaml ใหม่ทั้งหมด (เขียนไฟล์ให้อัตโนมัติ ไม่ต้อง copy-paste hash เอง)
"""

import bcrypt
import yaml
from pathlib import Path
import getpass

CONFIG_PATH = Path(__file__).parent / "config" / "users.yaml"

ACCOUNTS = [
    {"username": "admin",    "name": "ผู้ดูแลระบบ",                      "role": "admin"},
    {"username": "governor", "name": "ผู้ว่าการการทางพิเศษแห่งประเทศไทย", "role": "governor"},
    {"username": "exec01",   "name": "ผู้บริหารระดับสูง",                 "role": "executive"},
    {"username": "staff01",  "name": "เจ้าหน้าที่ปฏิบัติการ",             "role": "viewer"},
]

def main():
    print("=" * 60)
    print("ตั้งรหัสผ่านใหม่สำหรับผู้ใช้งานทั้ง 4 บัญชี")
    print("(พิมพ์รหัสผ่านแล้วกด Enter — ตัวอักษรจะไม่แสดงบนหน้าจอ เพื่อความปลอดภัย)")
    print("=" * 60)

    users_data = {"users": {}}

    for acc in ACCOUNTS:
        while True:
            pw1 = getpass.getpass(f"\nตั้งรหัสผ่านสำหรับ [{acc['username']}] ({acc['name']}): ")
            pw2 = getpass.getpass(f"พิมพ์รหัสผ่านอีกครั้งเพื่อยืนยัน: ")
            if pw1 != pw2:
                print("❌ รหัสผ่านไม่ตรงกัน กรุณาลองใหม่")
                continue
            if len(pw1) < 4:
                print("❌ รหัสผ่านสั้นเกินไป กรุณาตั้งอย่างน้อย 4 ตัวอักษร")
                continue
            break

        hashed = bcrypt.hashpw(pw1.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        users_data["users"][acc["username"]] = {
            "name": acc["name"],
            "role": acc["role"],
            "password_hash": hashed,
        }
        print(f"✅ ตั้งรหัสผ่านสำหรับ {acc['username']} สำเร็จ")

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(users_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("\n" + "=" * 60)
    print(f"🎉 เสร็จสิ้น! บันทึกไฟล์ที่: {CONFIG_PATH}")
    print("=" * 60)
    print("\nสรุปบัญชีผู้ใช้งาน (จดจำรหัสผ่านที่ตั้งไว้ให้ดี):")
    for acc in ACCOUNTS:
        print(f"  • {acc['username']:10s} → {acc['name']} ({acc['role']})")

if __name__ == "__main__":
    main()