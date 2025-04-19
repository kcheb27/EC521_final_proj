from flask import Flask, request, jsonify
from flasgger import Swagger
import os
import sqlite3
from Basic_USB_interface import (
    find_usb_drive, create_database, add_credentials, show_credentials,
    encrypt_file, decrypt_file
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
    Add a new password record to the encrypted database.

    ---
    tags:
      - Password Storage
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - url
              - username
              - password
            properties:
              url:
                type: string
              username:
                type: string
              password:
                type: string
    responses:
      200:
        description: Password added successfully
      400:
        description: Missing required fields
      500:
        description: Internal error
    """
    data = request.json
    url = data.get("url")
    username = data.get("username")
    password = data.get("password")
    if not all([url, username, password]):
        return jsonify({"error": "Missing field"}), 400
    try:
        usb_path = find_usb_drive()
        add_credentials(usb_path, url, username, password)
        return jsonify({"status": "added"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/passwords/<site>", methods=["GET"])
@with_decrypted_db
def get_password_by_site(site):
    """
    Retrieve password record for a specific site.

    ---
    tags:
      - Password Storage
    parameters:
      - name: site
        in: path
        required: true
        schema:
          type: string
        description: Website domain or URL
    responses:
      200:
        description: Password entry found
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
      404:
        description: No password entry for site
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM credentials WHERE url = ?", (site,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({"username": row[0], "password": row[1]})
    else:
        return jsonify({"error": "Not found"}), 404


@app.route("/api/passwords", methods=["GET"])
@with_decrypted_db
def get_all_passwords():
    """
    Retrieve all stored credentials in decrypted form.

    ---
    tags:
      - Password Storage
    responses:
      200:
        description: List of all credentials
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  url:
                    type: string
                  username:
                    type: string
                  password:
                    type: string
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, username, password FROM credentials")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {"url": row[0], "username": row[1], "password": row[2]}
        for row in rows
    ])


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
