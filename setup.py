import os
import base64
import getpass
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes

def generate_salt():
    return os.urandom(16)

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def get_cipher(password: str, salt: bytes) -> Fernet:
    key = derive_key(password, salt)
    return Fernet(key)

def init_setup():
    if os.path.exists("salt.bin") or os.path.exists("check.bin"):
        print("❗ Setup already completed. Remove existing files if you want to reset.")
        return

    # 1. Ask for master password twice
    pwd1 = getpass.getpass("Set a master password: ")
    pwd2 = getpass.getpass("Re-enter to confirm: ")

    if pwd1 != pwd2:
        print("❌ Passwords do not match. Aborting.")
        return

    # 2. Generate and save salt
    salt = generate_salt()
    with open("salt.bin", "wb") as f:
        f.write(salt)
    print("[✓] salt.bin created.")

    # 3. Derive encryption key and cipher
    cipher = get_cipher(pwd1, salt)

    # 4. Encrypt and save test string to check.bin
    check_data = cipher.encrypt(b"master_check_string")
    with open("check.bin", "wb") as f:
        f.write(check_data)
    print("[✓] check.bin created.")

    print("\n🎉 Setup complete. You can now start the password manager.")

if __name__ == "__main__":
    init_setup()
