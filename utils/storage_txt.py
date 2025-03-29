import os

def get_password_for_site(site: str, cipher):
    if not site:
        return None

    if not os.path.exists("vault.txt"):
        return None

    with open("vault.txt", "r") as f:
        for line in f:
            line = line.strip()
            try:
                decrypted = cipher.decrypt(line.encode()).decode()
                s, u, p = decrypted.split("|")
                if s == site:
                    return {"username": u, "password": p}
            except:
                continue

    return None
