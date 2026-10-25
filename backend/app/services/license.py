"""Reup Tool — License: key Ed25519 + dùng thử.

Mô hình (xem docs kế hoạch thương mại):
- Key do người bán ký bằng private key (file license_private.pem — KHÔNG commit,
  chỉ người bán giữ). Tool chỉ chứa PUBLIC key nên không ai tự ký key giả được.
- Key format: RT-<base64url(payload_json + "." + signature_b64)>.
  Payload: {plan: personal|pro|team, months: N (0 = vĩnh viễn), issued: YYYY-MM-DD}.
- Kích hoạt: verify chữ ký → gắn máy (machine ID) vào license.json.
  personal 1 máy, pro 3 máy, team 5 máy.
- Chưa có key: dùng thử 7 ngày / 10 video (trial.json, tạo lúc check đầu tiên).
- Dev bypass (chỉ người bán test): env REUP_LICENSE_DEV=1.
"""
import base64
import hashlib
import json
import os
import platform
import uuid
from datetime import date, timedelta

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LICENSE_PATH = os.path.join(ROOT, "license.json")
TRIAL_PATH = os.path.join(ROOT, "trial.json")

# Public key — công khai được, chỉ dùng để VERIFY (không ký được).
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEANqztRNMrqoDL9TAvjslX518KJuOfgusLIIBRWhRdHGw=
-----END PUBLIC KEY-----"""

PLAN_MACHINES = {"personal": 1, "pro": 3, "team": 5}
TRIAL_DAYS = 7
TRIAL_VIDEOS = 10


def machine_id() -> str:
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _verify_key(key: str):
    """Trả về payload nếu chữ ký hợp lệ, ngược lại None."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        if not key.startswith("RT-"):
            return None
        raw = base64.urlsafe_b64decode(key[3:] + "=" * (-len(key[3:]) % 4))
        payload_b, sig_b = raw.rsplit(b".", 1)
        pub = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
        pub.verify(bytes.fromhex(sig_b.decode()), payload_b)
        payload = json.loads(payload_b)
        if payload.get("plan") not in PLAN_MACHINES:
            return None
        return payload
    except Exception:
        return None


def get_status() -> dict:
    """Trạng thái license hiện tại (không raise)."""
    if os.environ.get("REUP_LICENSE_DEV") == "1":
        return {"mode": "dev", "plan": "dev", "machine_id": machine_id(),
                "note": "Dev bypass (env REUP_LICENSE_DEV=1)"}
    lic = _load_json(LICENSE_PATH)
    mid = machine_id()
    if lic.get("key"):
        payload = _verify_key(lic["key"])
        machines = lic.get("machines", [])
        if payload and mid in machines:
            exp = lic.get("exp")
            days_left = None
            if exp:
                days_left = (date.fromisoformat(exp) - date.today()).days
                if days_left < 0:
                    return {"mode": "expired", "plan": payload["plan"],
                            "machine_id": mid, "exp": exp}
            return {"mode": "licensed", "plan": payload["plan"],
                    "machine_id": mid, "exp": exp, "days_left": days_left,
                    "updates_until": lic.get("updates_until"),
                    "machines_used": len(machines),
                    "machines_max": PLAN_MACHINES[payload["plan"]]}
        return {"mode": "invalid", "plan": None, "machine_id": mid,
                "error": "Key không hợp lệ hoặc máy này chưa được gắn vào key"}
    # Trial
    tr = _load_json(TRIAL_PATH)
    if not tr.get("started"):
        tr = {"started": date.today().isoformat(), "videos_used": 0}
        with open(TRIAL_PATH, "w") as f:
            json.dump(tr, f)
    start = date.fromisoformat(tr["started"])
    days_left = TRIAL_DAYS - (date.today() - start).days
    videos_left = TRIAL_VIDEOS - int(tr.get("videos_used", 0))
    if days_left < 0 or videos_left <= 0:
        return {"mode": "expired", "plan": "trial", "machine_id": mid,
                "days_left": max(days_left, 0), "videos_left": max(videos_left, 0)}
    return {"mode": "trial", "plan": "trial", "machine_id": mid,
            "days_left": days_left, "videos_left": videos_left}


def activate(key: str) -> dict:
    """Gắn key vào máy này. Trả về status hoặc raise ValueError."""
    payload = _verify_key(key.strip())
    if not payload:
        raise ValueError("Key không hợp lệ (sai chữ ký hoặc sai định dạng)")
    mid = machine_id()
    lic = _load_json(LICENSE_PATH)
    machines = lic.get("machines", []) if lic.get("key") == key.strip() else []
    if mid not in machines:
        if len(machines) >= PLAN_MACHINES[payload["plan"]]:
            raise ValueError(
                f"Key đã gắn đủ {PLAN_MACHINES[payload['plan']]} máy — liên hệ người bán để reset")
        machines.append(mid)
    months = int(payload.get("months") or 0)
    issued = date.fromisoformat(payload["issued"]) if payload.get("issued") else date.today()
    exp = (issued + timedelta(days=30 * months)).isoformat() if months else None
    updates_until = (date.today() + timedelta(days=365)).isoformat()
    with open(LICENSE_PATH, "w") as f:
        json.dump({"key": key.strip(), "machines": machines, "exp": exp,
                   "updates_until": updates_until}, f, indent=1)
    return get_status()


def check_or_raise():
    """Chặn tạo job khi hết quyền. Trả về status nếu OK, raise RuntimeError nếu không."""
    st = get_status()
    if st["mode"] in ("licensed", "dev"):
        return st
    if st["mode"] == "trial":
        return st
    raise RuntimeError(
        "Hết dùng thử / key hết hạn — nhập key bản quyền ở Dashboard để tiếp tục")


def count_trial_video():
    """Ghi nhận 1 video dùng thử (chỉ khi đang ở trial)."""
    st = get_status()
    if st["mode"] != "trial":
        return
    tr = _load_json(TRIAL_PATH)
    tr["videos_used"] = int(tr.get("videos_used", 0)) + 1
    with open(TRIAL_PATH, "w") as f:
        json.dump(tr, f)
