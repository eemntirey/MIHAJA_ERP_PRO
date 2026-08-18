from cryptography.fernet import Fernet
import os


def _get_key():
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is required. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return key


def encrypt_text(value: str) -> str:
    key = _get_key().encode('utf-8')
    return Fernet(key).encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_text(token: str) -> str:
    key = _get_key().encode('utf-8')
    return Fernet(key).decrypt(token.encode('utf-8')).decode('utf-8')
