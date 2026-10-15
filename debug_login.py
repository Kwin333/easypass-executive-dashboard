"""debug_login.py — ตรวจ users.yaml + ทดสอบ login ทีละขั้น"""
import bcrypt, yaml, getpass, sys
from pathlib import Path

CONFIG = Path(__file__).parent / "config" / "users.yaml"

print("=" * 60)
print("🔍 DIAGNOSTIC LOGIN")
print("=" * 60)

# 1) ไฟล์มีจริงไหม
print(f"\n[1] CONFIG_PATH = {CONFIG}")
print(f"    exists = {CONFIG.exists()}")
if not CONFIG.exists():
    sys.exit("❌ ไม่พบไฟล์ → รัน: python manage_users.py")

# 2) ตรวจ BOM
raw = CONFIG.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
print(f"\n[2] BOM check: {'❌ มี BOM!' if has_bom else '✅ ไม่มี BOM'}")
print(f"    bytes[0:10] = {raw[:10]!r}")

# 3) parse YAML
with open(CONFIG, "r", encoding="utf-8-sig" if has_bom else "utf-8") as f:
    data = yaml.safe_load(f)

print(f"\n[3] YAML top-level keys = {list(data.keys())}")
users = data.get("users", {})
print(f"    users = {list(users.keys())}")

# 4) ตรวจ hash แต่ละคน
print("\n[4] ตรวจ hash แต่ละบัญชี")
print(f"    {'user':10s} {'role':10s} {'hash_prefix':14s} {'len':4s} {'ok':3s}")
for u, rec in users.items():
    h = rec.get("password_hash", "")
    ok = h.startswith(("$2a$", "$2b$", "$2y$")) and len(h) == 60
    print(f"    {u:10s} {rec.get('role',''):10s} {h[:14]:14s} {len(h):<4d} {'✅' if ok else '❌'}")

# 5) ทดสอบ login จริง
print("\n[5] ทดสอบ login")
username = input("    username: ").strip()
password = getpass.getpass("    password: ")

rec = users.get(username)
if not rec:
    print(f"    ❌ ไม่พบ user '{username}' ใน yaml")
    print(f"       → keys ที่มี: {list(users.keys())}")
    print(f"       → ระวัง: อาจมีช่องว่างท้ายชื่อ หรือ keyboard ผิดโหมด")
    sys.exit(1)

stored = rec["password_hash"]
print(f"    🔑 stored hash = {stored}")

try:
    ok = bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    print(f"\n    {'✅ รหัสผ่านถูกต้อง — login ได้แน่นอน' if ok else '❌ รหัสผ่านไม่ตรงกับ hash'}")
    if not ok:
        print(f"    password ที่คุณพิมพ์: {password!r}")
        print(f"    ความยาว: {len(password)} ตัวอักษร")
        print(f"    → ลองตรวจ Caps Lock / Thai keyboard / ช่องว่างท้าย")
except Exception as e:
    print(f"    💥 bcrypt error: {type(e).__name__}: {e}")

print("\n" + "=" * 60)