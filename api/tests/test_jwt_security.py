"""JWT validation hardening tests."""
from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.core.time import utc_now


def _configure_jwt(monkeypatch, issuer: str, audience: str) -> None:
    monkeypatch.setattr(settings, "JWT_ISSUER", issuer, raising=False)
    monkeypatch.setattr(settings, "JWT_AUDIENCE", audience, raising=False)


def test_decode_token_accepts_valid_issuer_and_audience(monkeypatch):
    issuer = "https://issuer.example.com"
    audience = "mrm-api"
    _configure_jwt(monkeypatch, issuer, audience)

    token = create_access_token({"sub": "user@example.com"})
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["iss"] == issuer
    assert payload["aud"] == audience


def test_decode_token_rejects_wrong_issuer(monkeypatch):
    issuer = "https://issuer.example.com"
    audience = "mrm-api"
    _configure_jwt(monkeypatch, issuer, audience)

    payload = {
        "sub": "user@example.com",
        "iss": "https://wrong-issuer.example.com",
        "aud": audience,
        "exp": utc_now() + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    assert decode_token(token) is None


def test_decode_token_rejects_wrong_audience(monkeypatch):
    issuer = "https://issuer.example.com"
    audience = "mrm-api"
    _configure_jwt(monkeypatch, issuer, audience)

    payload = {
        "sub": "user@example.com",
        "iss": issuer,
        "aud": "wrong-audience",
        "exp": utc_now() + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    assert decode_token(token) is None


def test_decode_token_rejects_wrong_algorithm(monkeypatch):
    issuer = "https://issuer.example.com"
    audience = "mrm-api"
    _configure_jwt(monkeypatch, issuer, audience)

    payload = {
        "sub": "user@example.com",
        "iss": issuer,
        "aud": audience,
        "exp": utc_now() + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS512")

    assert decode_token(token) is None
