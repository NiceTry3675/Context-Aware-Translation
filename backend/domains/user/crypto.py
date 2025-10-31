"""Utility helpers for encrypting API credentials."""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

from backend.config.settings import get_settings


def _load_encryption_key() -> bytes:
    """Return the Fernet key, generating a temporary one for development."""

    raw_key = os.getenv("API_KEY_ENCRYPTION_KEY")

    if raw_key:
        return raw_key.encode()

    settings = get_settings()
    if getattr(settings, "is_production", False):
        raise ValueError("API_KEY_ENCRYPTION_KEY must be set in a production environment.")

    generated_key = Fernet.generate_key()
    logging.warning(
        "No API_KEY_ENCRYPTION_KEY found. Generated a temporary key for development. "
        "All encrypted data will be lost on restart."
    )
    return generated_key


ENCRYPTION_KEY = _load_encryption_key()

# Initialize Fernet cipher
_fernet = Fernet(ENCRYPTION_KEY)


def encrypt_api_key(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypt a plain text API key.

    Args:
        plain_text: The plain text API key to encrypt

    Returns:
        The encrypted API key as a string, or None if input is None
    """
    if not plain_text:
        return None

    encrypted_bytes = _fernet.encrypt(plain_text.encode())
    return encrypted_bytes.decode()


def decrypt_api_key(encrypted_text: Optional[str]) -> Optional[str]:
    """
    Decrypt an encrypted API key.

    Args:
        encrypted_text: The encrypted API key to decrypt

    Returns:
        The decrypted API key as a string, or None if input is None
    """
    if not encrypted_text:
        return None

    decrypted_bytes = _fernet.decrypt(encrypted_text.encode())
    return decrypted_bytes.decode()
