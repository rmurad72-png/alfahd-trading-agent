"""
🔐 خزنة الفهد — تشفير API Keys
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_fernet = None


def init_vault(master_key: str, salt: str):
    """تهيئة Fernet بمفتاح مشتق من MASTER_KEY"""
    global _fernet
    if not master_key or not salt:
        logger.warning("⚠️ Vault: MASTER_KEY أو VAULT_SALT غير محدد — التشفير معطل")
        _fernet = None
        return

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    _fernet = Fernet(key)
    logger.info("🔐 Vault initialized")


def encrypt(text: str) -> str:
    if _fernet is None:
        return text
    return _fernet.encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    if _fernet is None:
        return token
    return _fernet.decrypt(token.encode()).decode()
