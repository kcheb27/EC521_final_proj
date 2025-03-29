import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes

def get_salt():
    with open("salt.bin", "rb") as f:
        return f.read()

def get_cipher(password: str) -> Fernet:
    salt = get_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key)
