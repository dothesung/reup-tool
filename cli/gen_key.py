#!/usr/bin/env python3
"""Seller tool — tạo key bản quyền Reup Tool (CHỈ người bán dùng).

Private key KHÔNG commit lên GitHub — giữ file license_private.pem trên máy
riêng (mật khẩu manager / USB). Public key đã nhúng trong services/license.py.

Dùng:
  # Lần đầu: tạo cặp key (chỉ chạy 1 lần, public key in ra để nhúng vào code)
  python3 cli/gen_key.py --gen-keys

  # Tạo key cho khách (key in ra gửi cho khách qua Zalo/email)
  python3 cli/gen_key.py --plan personal --private-key ./license_private.pem
  python3 cli/gen_key.py --plan pro --months 1 --private-key ./license_private.pem
  python3 cli/gen_key.py --plan team --months 12 --private-key ./license_private.pem
"""
import argparse
import base64
import json
from datetime import date

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def gen_keys():
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    with open("license_private.pem", "wb") as f:
        f.write(priv_pem)
    print("Đã ghi license_private.pem — CẤT KỸ, KHÔNG COMMIT, KHÔNG GỬI AI.")
    print("Nhúng public key này vào backend/app/services/license.py:")
    print(pub_pem.decode())


def make_key(plan: str, months: int, priv_path: str) -> str:
    with open(priv_path, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    payload = {"plan": plan, "months": months, "issued": date.today().isoformat()}
    payload_b = json.dumps(payload, separators=(",", ":")).encode()
    sig = priv.sign(payload_b)
    raw = payload_b + b"." + sig.hex().encode()
    return "RT-" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-keys", action="store_true")
    ap.add_argument("--plan", choices=["personal", "pro", "team"], default="personal")
    ap.add_argument("--months", type=int, default=0,
                    help="0 = vĩnh viễn (chỉ personal), >0 = số tháng thuê bao")
    ap.add_argument("--private-key", default="./license_private.pem")
    a = ap.parse_args()
    if a.gen_keys:
        gen_keys()
    else:
        print(make_key(a.plan, a.months, a.private_key))
