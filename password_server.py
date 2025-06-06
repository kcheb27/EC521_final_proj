"""
FastAPI service ⇆ Chrome extension ⇆ encrypted USB database
-----------------------------------------------------------

Relies on Basic_USB_interface.py (same folder).

• Each request supplies a **passphrase** string (not raw key).
• Server uses `derive_aes_key(passphrase)` to deterministically generate AES-256 key.
• The derived key is then used to encrypt/decrypt passwords.db on the USB stick.

Workflow per request:
---------------------
    1. Server receives passphrase (as POST or GET query)
    2. Derive AES key using PBKDF2-HMAC-SHA256 (with fixed salt)
    3. Decrypt passwords.db on the USB stick
    4. Copy the clear DB to a CLOSED temp file
    5. Run SQL callback on that temp DB
    6. Copy temp DB back, re-encrypt, clean up

Endpoints (Updated)
-------------------
POST /savePassword
    →  { "site", "username", "password", "passphrase" }

GET  /getPassword/{site}?passphrase=xxx
    →  Returns matching credentials if any

POST /importFromUSB
    →  { "items": [...], "passphrase": ... }

GET  /exportToUSB?passphrase=xxx
    →  Plaintext credentials export

POST /setupUSB
    →  { "passphrase": ... } — creates and encrypts new DB

POST /encryptUSB
    →  { "passphrase": ... } — encrypts existing DB (if not encrypted)

GET  /usbStatus
    →  Returns whether USB is connected, DB exists, and whether it is encrypted

Run:
----
    uvicorn password_server:app --host 127.0.0.1 --port 5000 --reload
"""
import os
import shutil
import sqlite3
import tempfile
import typing as t
import binascii

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from Basic_USB_interface import (
    find_usb_drive,
    create_database,
    encrypt_file,
    decrypt_file,
    derive_aes_key
)

# ---------- USB paths ------------------------------------------------
USB_PATH = find_usb_drive()
# if not USB_PATH:
#     raise RuntimeError("No USB drive detected – insert one before starting the service.")
print(f"USB drive found at: {USB_PATH}")

if USB_PATH:
    DB_FILE = os.path.join(USB_PATH, "passwords.db")
else:
    DB_FILE = ""


# ---------- helpers --------------------------------------------------
# def _ensure_db() -> None:
#     """Create passwords.db (encrypted) if it doesn’t exist yet."""
#     if not os.path.exists(DB_FILE):
#         create_database(USB_PATH)
#         # leave it UNencrypted for the very first run; caller will encrypt

# _ensure_db()


def _with_decrypted_db(hex_key: str, callback):
    """
    • Validate key, decrypt main DB.
    • Work on a temp copy so the open window is tiny.
    • Re‑encrypt and clean up even if callback throws.
    """
    try:
        key = bytes.fromhex(hex_key)
        if len(key) != 32:
            raise ValueError
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Invalid master key format. Must be 64 hex characters.")

    try:
        # Try to decrypt using the given key
        decrypt_file(DB_FILE, key)
    except Exception:
        raise HTTPException(400, Exception + "Incorrect passphrase. Failed to decrypt database.")

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    shutil.copyfile(DB_FILE, tmp_path)

    try:
        conn = sqlite3.connect(tmp_path)
        result = callback(conn)
        conn.commit()
        conn.close()

        shutil.copyfile(tmp_path, DB_FILE)
        encrypt_file(DB_FILE, key)
        return result
    finally:
        os.remove(tmp_path)



# ---------- FastAPI setup -------------------------------------------
app = FastAPI(title="USB‑Encrypted Password API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost",
        "http://127.0.0.1",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- API routes ----------------------------------------------
@app.post("/savePassword")
def save_password(data: dict):
    site      = data.get("site")
    username  = data.get("username")
    pw        = data.get("password")
    key       = derive_aes_key(data.get("masterKey")) # Derive AES key
    force     = bool(data.get("force"))          # allow optional overwrite

    if not all([site, username, pw, key]):
        raise HTTPException(400, "site, username, password, masterKey required")

    def _upsert(conn: sqlite3.Connection):
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM credentials WHERE url = ? AND username = ?",
            (site, username),
        )
        exists = cur.fetchone() is not None

        if exists and not force:
            return {"status": "exists"}

        if exists:
            cur.execute(
                "UPDATE credentials SET password = ? WHERE url = ? AND username = ?",
                (pw, site, username),
            )
            return {"status": "overwritten"}
        else:
            cur.execute(
                "INSERT INTO credentials (url, username, password) VALUES (?,?,?)",
                (site, username, pw),
            )
            return {"status": "success"}


    # send the callback's result straight to the client
    return _with_decrypted_db(key, _upsert)


@app.get("/getPassword/{site}")
def get_password(site: str, key: str = Query(..., alias="key")):
    key = derive_aes_key(key) # Derive AES key
    def _lookup(conn: sqlite3.Connection):
        cur = conn.cursor()
        cur.execute(
            "SELECT username, password FROM credentials WHERE url = ?",
            (site,),
        )
        row = cur.fetchone()
        return {"username": row[0], "password": row[1]} if row else None

    entry = _with_decrypted_db(key, _lookup)
    return {"entry": entry}


# @app.post("/importFromUSB")
# def import_from_usb(payload: dict):
#     items: t.List[dict] = payload.get("items", [])
#     key: str = payload.get("masterKey")
#     key = derive_aes_key(key) # Derive AES key
#     if not key or not items:
#         raise HTTPException(400, "items[] and masterKey required")

#     def _bulk(conn: sqlite3.Connection):
#         conn.executemany(
#             """
#             INSERT OR REPLACE INTO credentials (url, username, password)
#             VALUES (?,?,?)
#             """,
#             [(i["site"], i["username"], i["password"]) for i in items],
#         )

#     _with_decrypted_db(key, _bulk)
#     return {"status": "imported", "count": len(items)}


# @app.get("/exportToUSB", response_class=PlainTextResponse)
# def export_to_usb(key: str = Query(..., alias="key")):
#     key = derive_aes_key(key) # Derive AES key
#     def _dump(conn: sqlite3.Connection):
#         cur = conn.cursor()
#         cur.execute("SELECT url, username, password FROM credentials")
#         rows = cur.fetchall()
#         lines = ["=== Saved Passwords ===", ""]
#         for i, (url, user, pw) in enumerate(rows, 1):
#             lines += [
#                 f"Entry #{i}",
#                 f"Website: {url}",
#                 f"Username: {user}",
#                 f"Password: {pw}",
#                 "",
#             ]
#         lines.append(f"=== Total: {len(rows)} passwords ===")
#         return "\n".join(lines)

#     return _with_decrypted_db(key, _dump)


@app.get("/usbStatus") # Check if: usb plugged in, db exists, db encrypted. Update: When calling this function, it detects usb path and db path
def usb_status():
    usb_path = find_usb_drive()
    if not usb_path:
        return {"usbFound": False}

    db_path = os.path.join(usb_path, "passwords.db")
    db_exists = os.path.exists(db_path)

    encrypted = False
    if db_exists:
        try:
            with open(db_path, 'rb') as f:
                sig = f.read(16) # if SQLite db is not encrypted it shoud start with:
            if not sig.startswith(b"SQLite format 3"):
                encrypted = True
        except:
            encrypted = True

    global USB_PATH 
    USB_PATH = usb_path
    global DB_FILE
    DB_FILE = db_path

    return {
        "usbFound": True,
        "dbExists": db_exists,
        "encrypted": encrypted,
        "usbPath": usb_path,
        "dbPath": db_path
    }



@app.post("/setupUSB")
def setup_usb(data: dict):
    key_hex = data.get("masterKey") # which is now passphrase
    key_hex = derive_aes_key(key_hex) # Derive 64-AES key
    if not key_hex:
        raise HTTPException(400, "masterKey is required")

    try:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError
    except Exception:
        raise HTTPException(400, "masterKey must be 64 hexadecimal characters(derive AES key error)")

    usb_path = find_usb_drive()
    if not usb_path:
        raise HTTPException(500, "No USB drive found.")

    db_path = os.path.join(usb_path, "passwords.db")

    if os.path.exists(db_path):
        raise HTTPException(400, "Database already exists. Use /encryptUSB instead.")

    create_database(usb_path)
    encrypt_file(db_path, key)

    return {"status": "success", "message": "Database created and encrypted."}


@app.post("/encryptUSB")  # In case DB is  already created but not encrypted
def encrypt_usb(data: dict):
    key_hex = data.get("masterKey") # which is now passphrase
    key_hex = derive_aes_key(key_hex) # Derive 64-AES key
    if not key_hex:
        raise HTTPException(400, "masterKey is required")

    try:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError
    except Exception:
        raise HTTPException(400, "masterKey must be 64 hexadecimal characters")

    usb_path = find_usb_drive()
    if not usb_path:
        raise HTTPException(500, "No USB drive found.")

    db_path = os.path.join(usb_path, "passwords.db")
    if not os.path.exists(db_path):
        raise HTTPException(404, "Database file does not exist.")

    try:
        with open(db_path, 'rb') as f:
            sig = f.read(16)
        if not sig.startswith(b"SQLite format 3"):
            return {"status": "already_encrypted"}
    except:
        return {"status": "unknown", "message": "Failed to verify encryption state."}

    encrypt_file(db_path, key)
    return {"status": "success", "message": "Database encrypted."}





# ---------- local runner --------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000, reload=False)
