from flask import Flask, request, jsonify
from flasgger import Swagger
import os, sqlite3
from functools import wraps
from Basic_USB_interface import (
    find_usb_drive, create_database, add_credentials,
    encrypt_file, decrypt_file,
    derive_aes_key, decrypt_payload, encrypt_response
)

from flask_cors import CORS
app = Flask(__name__)
CORS(app)          # ← 新增
# Swagger(app)

Swagger(app)

# ---------- helpers ----------
def get_db_path():
    usb = find_usb_drive()
    if not usb:
        raise Exception("No USB drive found")
    return os.path.join(usb, "passwords.db")

def with_decrypted_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        body = request.json or {}
        db_pass = body.get("db_password")
        if not db_pass:
            return jsonify({"error": "Missing 'db_password'"}), 400
        key = derive_aes_key(db_pass)
        db_path = get_db_path()
        try:
            decrypt_file(db_path, key)
        except Exception as e:
            return jsonify({"error": f"DB decrypt failed: {e}"}), 400
        try:
            res = func(*args, **kwargs)
        finally:
            encrypt_file(db_path, key)
        return res
    return wrapper

# ---------- API ----------
@app.route("/api/passwords", methods=["POST"])
@with_decrypted_db
def add_password():
    """
    Add new credential (payload encrypted with communication password)

    ---
    tags: [Password Storage]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [iv, ciphertext, password, db_password]
    """
    body = request.json
    comm_pass = body.get("password")
    if not comm_pass:
        return jsonify({"error": "Missing communication password"}), 400
    try:
        data = decrypt_payload(body, comm_pass)   # {url,username,password}
    except Exception as e:
        return jsonify({"error": f"decrypt_payload failed: {e}"}), 400

    usb = find_usb_drive()
    add_credentials(usb, data["url"], data["username"], data["password"])
    return jsonify({"status": "added"})

@app.route("/api/passwords/<site>", methods=["POST"])
@with_decrypted_db
def get_password(site):
    """
    Get single credential (response encrypted)

    ---
    tags: [Password Storage]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [password, db_password]
    """
    comm_pass = (request.json or {}).get("password")
    if not comm_pass:
        return jsonify({"error": "Missing communication password"}), 400

    db = sqlite3.connect(get_db_path())
    row = db.execute("SELECT username,password FROM credentials WHERE url=?", (site,)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify(encrypt_response({"username": row[0], "password": row[1]}, comm_pass))

@app.route("/api/passwords/all", methods=["POST"])
@with_decrypted_db
def list_passwords():
    """Return all credentials (encrypted)"""
    comm_pass = (request.json or {}).get("password")
    if not comm_pass:
        return jsonify({"error": "Missing communication password"}), 400

    db = sqlite3.connect(get_db_path())
    rows = db.execute("SELECT url,username,password FROM credentials").fetchall()
    db.close()
    return jsonify(encrypt_response(
        [{"url": u, "username": un, "password": pw} for u,un,pw in rows],
        comm_pass))

@app.route("/api/reset", methods=["POST"])
def reset_encrypt():
    """
    Manually re‑encrypt DB (needs db_password)
    ---
    tags: [Encryption]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [db_password]
    """
    db_pass = (request.json or {}).get("db_password")
    if not db_pass:
        return jsonify({"error": "Missing db_password"}), 400
    key = derive_aes_key(db_pass)
    try:
        encrypt_file(get_db_path(), key)
        return jsonify({"message": "Re‑encrypted OK"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
