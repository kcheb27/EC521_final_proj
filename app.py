from flask import Flask, request, jsonify
from flasgger import Swagger
import os
import sqlite3
from functools import wraps
from Basic_USB_interface import (
    find_usb_drive, create_database, add_credentials, show_credentials,
    encrypt_file, decrypt_file, decrypt_payload, derive_aes_key
)

app = Flask(__name__)
swagger = Swagger(app)

# In-memory AES key (hex string converted to bytes)
aes_key = None


def get_db_path():
    usb_path = find_usb_drive()
    if not usb_path:
        raise Exception("No USB drive found")
    return os.path.join(usb_path, 'passwords.db')


def with_decrypted_db(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not aes_key:
            return jsonify({"error": "AES key not set"}), 401
        db_path = get_db_path()
        decrypt_file(db_path, aes_key)
        try:
            result = func(*args, **kwargs)
        finally:
            encrypt_file(db_path, aes_key)
        return result
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/api/set-key", methods=["POST"])
def set_key():
    """
    Set AES-256 key to be used for encryption/decryption.

    ---
    tags:
      - Key Management
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - key
            properties:
              key:
                type: string
                description: 64-character AES key (hex)
    responses:
      200:
        description: Key accepted
      400:
        description: Invalid or missing AES key
    """
    global aes_key
    data = request.json
    key_hex = data.get("key")
    if not key_hex or len(key_hex) != 64:
        return jsonify({"error": "Invalid or missing AES key"}), 400
    try:
        aes_key = bytes.fromhex(key_hex)
    except Exception:
        return jsonify({"error": "AES key format invalid"}), 400
    return jsonify({"message": "Key accepted"}), 200


@app.route("/api/passwords", methods=["POST"])
@with_decrypted_db
def add_password():
    """
    Add a new password (fields encrypted from frontend).

    ---
    tags:
      - Password Storage
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [iv, ciphertext, password]
            properties:
              iv:
                type: string
              ciphertext:
                type: string
              password:
                type: string  # 主密码，用于派生通信 AES key（仅用于 API 解密）
    responses:
      200:
        description: Added
    """
    data = request.json
    password_for_decryption = data.get("password")
    if not password_for_decryption:
        return jsonify({"error": "Missing password"}), 400
    try:
        decrypted_payload = decrypt_payload(data, password_for_decryption)
    except Exception as e:
        return jsonify({"error": f"Decryption failed: {e}"}), 400

    
    url = decrypted_payload.get("url")
    username = decrypted_payload.get("username")
    password = decrypted_payload.get("password")

    usb_path = find_usb_drive()
    add_credentials(usb_path, url, username, password)
    return jsonify({"status": "added"})



@app.route("/api/passwords/<site>", methods=["POST"])
@with_decrypted_db
def get_password_by_site(site):
    """
    Retrieve password record for a specific site and return AES-encrypted payload.

    ---
    tags:
      - Password Storage
    parameters:
      - name: site
        in: path
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [password]
            properties:
              password:
                type: string
                description: The master password for response encryption
    responses:
      200:
        description: Encrypted password entry
    """
    from Basic_USB_interface import encrypt_response

    req = request.json
    password_for_encrypt = req.get("password")
    if not password_for_encrypt:
        return jsonify({"error": "Missing password"}), 400

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM credentials WHERE url = ?", (site,))
    row = cursor.fetchone()
    conn.close()

    if row:
        data = {"username": row[0], "password": row[1]}
        return jsonify(encrypt_response(data, password_for_encrypt))
    else:
        return jsonify({"error": "Not found"}), 404


@app.route("/api/passwords/all", methods=["POST"])
@with_decrypted_db
def get_all_passwords():
    """
    Retrieve all stored credentials and return encrypted payload.

    ---
    tags:
      - Password Storage
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [password]
            properties:
              password:
                type: string
                description: The master password for response encryption
    responses:
      200:
        description: Encrypted list of credentials
    """
    
    from Basic_USB_interface import encrypt_response

    req = request.json
    password_for_encrypt = req.get("password")
    if not password_for_encrypt:
        return jsonify({"error": "Missing password"}), 400

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, username, password FROM credentials")
    rows = cursor.fetchall()
    conn.close()

    data = [
        {"url": row[0], "username": row[1], "password": row[2]}
        for row in rows
    ]
    return jsonify(encrypt_response(data, password_for_encrypt))


@app.route("/api/reset", methods=["POST"])
def reset_encrypt():
    """
    Re-encrypt the password database (if already decrypted).

    ---
    tags:
      - Encryption
    responses:
      200:
        description: Database re-encrypted
      401:
        description: Key not set
      500:
        description: Internal error
    """
    if not aes_key:
        return jsonify({"error": "AES key not set"}), 401
    try:
        db_path = get_db_path()
        encrypt_file(db_path, aes_key)
        return jsonify({"message": "Re-encrypted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
