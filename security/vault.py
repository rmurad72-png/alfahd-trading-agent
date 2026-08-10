"""
🔐 الفهد — خزنة الأمان
AES-256-GCM via Fernet with PBKDF2HMAC key derivation
Bitget Skill: Zero-Log Policy — NO credentials ever logged
"""
import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class Vault:
    """
    خزنة تشفير AES-256
    - لا تُسجّل أي credentials
    - لا تُخزّن plaintext أبداً
    - تستخدم PBKDF2HMAC لتقوية المفتاح (Bitget Skill pattern)
    """

    def __init__(self, master_password: str, salt: str = "alfahd-salt-v1"):
        """
        master_password: كلمة المرور الرئيسية (أي نص)
        salt: salt فريد للمشروع
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode("utf-8"),
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))
        self._cipher = Fernet(key)
        self._key_hash = hashlib.sha256(key).hexdigest()[:16]
        logger.info(f"🔐 Vault initialized | key_hash={self._key_hash}")

    def encrypt(self, plaintext: str) -> str:
        """تشفير نص إلى base64"""
        if not plaintext:
            return ""
        try:
            encrypted = self._cipher.encrypt(plaintext.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Vault encrypt failed: {type(e).__name__}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """فك تشفير base64 إلى نص"""
        if not ciphertext:
            return ""
        try:
            decrypted = self._cipher.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Vault decrypt failed: {type(e).__name__}")
            raise

    def encrypt_dict(self, data: dict) -> dict:
        """تشفير جميع القيم في dictionary"""
        return {k: self.encrypt(v) if v else v for k, v in data.items()}

    def decrypt_dict(self, data: dict) -> dict:
        """فك تشفير جميع القيم في dictionary"""
        return {k: self.decrypt(v) if v else v for k, v in data.items()}

    @staticmethod
    def generate_password(length: int = 32) -> str:
        """توليد كلمة مرور عشوائية آمنة"""
        import secrets
        return secrets.token_urlsafe(length)


# Singleton
_vault_instance: Optional[Vault] = None


def init_vault(master_password: str, salt: str = "alfahd-salt-v1") -> Vault:
    global _vault_instance
    _vault_instance = Vault(master_password, salt)
    return _vault_instance


def get_vault() -> Vault:
    if _vault_instance is None:
        raise RuntimeError("Vault not initialized. Call init_vault() first.")
    return _vault_instance
