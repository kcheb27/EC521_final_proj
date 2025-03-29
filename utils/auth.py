def verify_master_password(cipher) -> bool:
    try:
        with open("check.bin", "rb") as f:
            encrypted = f.read()
        decrypted = cipher.decrypt(encrypted).decode()
        return decrypted == "master_check_string"
    except:
        return False
