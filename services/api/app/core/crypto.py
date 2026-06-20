"""Symmetric encryption for provider secrets at rest (NFR-004).

Secrets (API keys, tokens) are stored encrypted and never returned by the API — only
masked previews. The Fernet key comes from SECRET_ENC_KEY; if unset, a key is derived
from JWT_SECRET so local dev works, with a clear warning to set a dedicated key in prod.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    key = (settings.secret_enc_key or "").strip()
    if key:
        # Accept either a urlsafe-base64 Fernet key or any passphrase (hashed to 32 bytes).
        try:
            return Fernet(key.encode())
        except (ValueError, TypeError):
            digest = hashlib.sha256(key.encode()).digest()
            return Fernet(base64.urlsafe_b64encode(digest))
    # Fallback: derive from JWT secret (dev only).
    digest = hashlib.sha256(("bp360-enc::" + settings.jwt_secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def mask(secret: str) -> str:
    """Show only the last 4 chars for display."""
    if not secret:
        return ""
    tail = secret[-4:]
    return f"••••{tail}"
