from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.utils import timezone
import json


def _signer():
    return TimestampSigner()


def make_share_token(slug, variant, fmt, rounds=None):
    payload = {
        "slug": slug,
        "variant": variant,
        "format": fmt,
        "rounds": rounds or [],
        "ts": int(timezone.now().timestamp()),
    }
    data = json.dumps(payload, separators=(",", ":"))
    return _signer().sign(data)


def verify_share_token(token):
    ttl_days = getattr(settings, "MSA_SHARE_TTL_DAYS", 7)
    try:
        raw = _signer().unsign(token, max_age=ttl_days * 86400)
        payload = json.loads(raw)
    except (BadSignature, SignatureExpired, json.JSONDecodeError):
        return None
    return payload
