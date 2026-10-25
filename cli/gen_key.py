#!/usr/bin/env python3
"""Seller tool — tạo key bản quyền Reup Tool (CHỈ người bán dùng).

Private key KHÔNG commit lên GitHub — giữ file license_private.pem trên máy
riêng (mật khẩu manager / USB). Public key đã nhúng trong services/license.py.

Dùng (chạy bằng venv python, vd: .venv/bin/python cli/gen_key.py ...):
  # Lần đầu: tạo cặp key (chỉ chạy 1 lần, public key in ra để nhúng vào code)
  python3 cli/gen_key.py --gen-keys

  # Tạo key cho khách (key in ra gửi cho khách qua Zalo/email, đồng thời ghi sổ)
  python3 cli/gen_key.py --plan personal --private-key ./license_private.pem --note "Anh A"
  python3 cli/gen_key.py --plan pro --months 1 --private-key ./license_private.pem
  python3 cli/gen_key.py --plan team --months 12 --private-key ./license_private.pem
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services import license as lic


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-keys", action="store_true")
    ap.add_argument("--plan", choices=["personal", "pro", "team"], default="personal")
    ap.add_argument("--months", type=int, default=0,
                    help="0 = vĩnh viễn (chỉ personal), >0 = số tháng thuê bao")
    ap.add_argument("--private-key", default="./license_private.pem")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    if a.gen_keys:
        gen_keys()
    else:
        with open(a.private_key, "rb") as f:
            key = lic.create_key(a.plan, a.months, f.read())
        lic.record_issued(key, a.plan, a.months, a.note)
        print(key)
