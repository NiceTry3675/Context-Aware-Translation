"""
Simple encryption utility for storing API keys securely.
Uses Fernet symmetric encryption from cryptography library.
"""
import os
from cryptography.fernet import Fernet
from typing import Optional

# Get encryption key from environment variable
# In production, this should be stored securely (e.g., in secrets manager)
ENCRYPTION_KEY = os.getenv("API_KEY_ENCRYPTION_KEY")

# If no key is set, generate one (for development only)
if not ENCRYPTION_KEY:
    # Generate a key and warn the user
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"WARNING: No API_KEY_ENCRYPTION_KEY found in environment. Using temporary key: {ENCRYPTION_KEY}")
    print("For production, set API_KEY_ENCRYPTION_KEY environment variable to a secure key.")

# Initialize Fernet cipher
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


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
