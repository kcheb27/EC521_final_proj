import os
import base64
import getpass
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes

# === Utility Functions ===

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

# === Salt Initialization ===

def init_salt():
    if not os.path.exists("salt.bin"):
        salt = generate_salt()
        with open("salt.bin", "wb") as f:
            f.write(salt)
        print("[✓] New salt generated.")
    else:
        print("[✓] Salt already exists.")

# === Master Password Check ===

def verify_master_password(cipher: Fernet):
    test_string = "test_verification_entry"
    encrypted = cipher.encrypt(test_string.encode())
    try:
        decrypted = cipher.decrypt(encrypted).decode()
        return decrypted == test_string
    except InvalidToken:
        return False

# === Add Encrypted Record ===

def add_password(cipher: Fernet):
    site = input("Site name: ")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    combined = f"{site}|{username}|{password}"
    encrypted = cipher.encrypt(combined.encode()).decode()

    with open("vault.txt", "a") as f:
        f.write(encrypted + "\n")
    print("[✓] Password encrypted and saved to vault.txt.")

# === Query and Decrypt Record ===

def query_password(cipher: Fernet):
    site = input("Enter site name to search: ")
    found = False

    if not os.path.exists("vault.txt"):
        print("❌ vault.txt not found.")
        return

    with open("vault.txt", "r") as f:
        for line in f:
            line = line.strip()
            try:
                decrypted = cipher.decrypt(line.encode()).decode()
                s, u, p = decrypted.split("|")
                if s == site:
                    print(f"Username: {u}")
                    print(f"Password: {p}")
                    found = True
            except:
                continue

    if not found:
        print("❌ Record not found or incorrect master password.")

# === List All Entries ===

def list_all_passwords(cipher: Fernet):
    if not os.path.exists("vault.txt"):
        print("❌ vault.txt not found.")
        return

    print("=== All Saved Entries ===")
    with open("vault.txt", "r") as f:
        for line in f:
            line = line.strip()
            try:
                decrypted = cipher.decrypt(line.encode()).decode()
                s, u, p = decrypted.split("|")
                print(f"[{s}] Username: {u} | Password: {p}")
            except:
                continue

# === Main Program ===

def main():
    init_salt()

    with open("salt.bin", "rb") as f:
        salt = f.read()

    # First input (visible)
    master_password = getpass.getpass("Enter your master password: ")
    # Second input (hidden verification)
    master_password_confirm = getpass.getpass("Re-enter to confirm: ")

    if master_password != master_password_confirm:
        print("❌ Master password mismatch. Aborting.")
        return

    cipher = get_cipher(master_password, salt)

    if not verify_master_password(cipher):
        print("❌ Invalid master password. Exiting.")
        return

    while True:
        print("\n1. Add password\n2. Query password\n3. List all\n4. Exit")
        choice = input("Select an option: ")
        if choice == '1':
            add_password(cipher)
        elif choice == '2':
            query_password(cipher)
        elif choice == '3':
            list_all_passwords(cipher)
        elif choice == '4':
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
