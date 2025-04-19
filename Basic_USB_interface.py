import os, psutil, sqlite3, json, base64, getpass
from hashlib import pbkdf2_hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# ---------- USB 帮助 ----------
def find_usb_drive():
    partitions = psutil.disk_partitions()
    if os.name == "nt":
        for p in partitions:
            if "removable" in p.opts.lower():
                return p.mountpoint
    else:
        for p in partitions:
            m = p.mountpoint
            if (m.startswith(("/Volumes/", "/media/", "/run/media/"))
                and "Recovery" not in m and "Preboot" not in m):
                return m
    return None

# ---------- SQLite ----------
def create_database(usb_path: str):
    db = os.path.join(usb_path, "passwords.db")
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS credentials(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               url TEXT NOT NULL,
               username TEXT NOT NULL,
               password TEXT NOT NULL );"""
    )
    conn.commit(); conn.close()

def add_credentials(usb_path, url, username, password):
    db = os.path.join(usb_path, "passwords.db")
    if not os.path.exists(db):
        create_database(usb_path)
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO credentials(url,username,password) VALUES(?,?,?)",
                 (url, username, password))
    conn.commit(); conn.close()

def show_credentials(usb_path):
    db = os.path.join(usb_path, "passwords.db")
    if not os.path.exists(db):
        print("passwords.db not found"); return
    for i,(u,un,pw) in enumerate(sqlite3.connect(db)
                                 .execute("SELECT url,username,password FROM credentials")
                                 .fetchall(),1):
        print(f"{i}. {u} – {un}:{pw}")

# ---------- 文件级 AES‑256‑CBC ----------
def _check32(key: bytes): 
    if len(key)!=32: raise ValueError("Key must be 32 bytes")

def encrypt_file(file_path, key: bytes):
    _check32(key)
    iv=os.urandom(16)
    cipher=Cipher(algorithms.AES(key),modes.CBC(iv),backend=default_backend())
    pad=padding.PKCS7(128).padder()
    with open(file_path,"rb") as f: plain=f.read()
    ct=cipher.encryptor().update(pad.update(plain)+pad.finalize())+cipher.encryptor().finalize()
    with open(file_path,"wb") as f: f.write(iv+ct)

def decrypt_file(file_path, key: bytes):
    _check32(key)
    with open(file_path,"rb") as f: data=f.read()
    iv,ct=data[:16],data[16:]
    cipher=Cipher(algorithms.AES(key),modes.CBC(iv),backend=default_backend())
    pt=cipher.decryptor().update(ct)+cipher.decryptor().finalize()
    pt=padding.PKCS7(128).unpadder().update(pt)+padding.PKCS7(128).unpadder().finalize()
    with open(file_path,"wb") as f: f.write(pt)

# ---------- PBKDF2 → AES key ----------
def derive_aes_key(password:str, length:int=32, iterations:int=100_000)->bytes:
    return pbkdf2_hmac("sha256", password.encode(), b"", iterations, dklen=length)

# ---------- 字段级加/解密（通信加密） ----------
def decrypt_payload(payload:dict, comm_pass:str)->dict:
    iv=base64.b64decode(payload["iv"])
    ct=base64.b64decode(payload["ciphertext"])
    key=derive_aes_key(comm_pass)
    cipher=Cipher(algorithms.AES(key),modes.CBC(iv),backend=default_backend())
    padded=cipher.decryptor().update(ct)+cipher.decryptor().finalize()
    data=padding.PKCS7(128).unpadder().update(padded)+padding.PKCS7(128).unpadder().finalize()
    return json.loads(data.decode())

def encrypt_response(data:dict, comm_pass:str)->dict:
    key=derive_aes_key(comm_pass)
    iv=os.urandom(16)
    raw=json.dumps(data).encode()
    padded=padding.PKCS7(128).padder().update(raw)+padding.PKCS7(128).padder().finalize()
    ct=Cipher(algorithms.AES(key),modes.CBC(iv),backend=default_backend())\
        .encryptor().update(padded)+Cipher(algorithms.AES(key),modes.CBC(iv),backend=default_backend())\
        .encryptor().finalize()
    return {"iv":base64.b64encode(iv).decode(),
            "ciphertext":base64.b64encode(ct).decode()}
