# US2 (feature 006): validate_webapp_init_data must enforce auth_date freshness (anti-replay).
# R-PROC-3: reproduces FR-005/006/007 before the check exists.
import json
import time
import hmac
import hashlib
import urllib.parse

import config
from web.auth import validate_webapp_init_data


def _sign(params: dict) -> str:
    """Builds a correctly HMAC-signed init-data string for the test BOT_TOKEN."""
    items = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)
    secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    signed = dict(params)
    signed["hash"] = h
    return urllib.parse.urlencode(signed)


def _init_data(auth_date=None, include_auth_date=True) -> str:
    params = {"user": json.dumps({"id": 42, "first_name": "T"})}
    if include_auth_date:
        params["auth_date"] = str(auth_date)
    return _sign(params)


def test_fresh_session_accepted():
    data = validate_webapp_init_data(_init_data(auth_date=int(time.time())))
    assert data is not None
    assert json.loads(data["user"])["id"] == 42


def test_stale_session_rejected():
    # ~2 days old, well beyond the 24h default TTL
    stale = int(time.time()) - 2 * 24 * 3600
    assert validate_webapp_init_data(_init_data(auth_date=stale)) is None


def test_missing_auth_date_rejected():
    assert validate_webapp_init_data(_init_data(include_auth_date=False)) is None


def test_future_beyond_skew_rejected():
    future = int(time.time()) + 600  # beyond 300s skew tolerance
    assert validate_webapp_init_data(_init_data(auth_date=future)) is None


def test_bad_signature_still_rejected():
    tampered = _init_data(auth_date=int(time.time())) + "0"
    assert validate_webapp_init_data(tampered) is None
