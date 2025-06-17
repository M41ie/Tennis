import os
import hashlib
import base64

class CryptContext:
    def __init__(self, schemes=None, deprecated="auto"):
        self.scheme = (schemes or ["pbkdf2_sha256"])[0]

    def hash(self, password: str) -> str:
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return f"{self.scheme}${salt.hex()}${base64.b64encode(dk).decode()}"

    def verify(self, password: str, hashed: str) -> bool:
        try:
            scheme, salt_hex, digest_b64 = hashed.split("$", 2)
        except ValueError:
            raise ValueError("Invalid hash format")
        if scheme != self.scheme:
            raise ValueError("Unsupported scheme")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return base64.b64encode(dk).decode() == digest_b64
