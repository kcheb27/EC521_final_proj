# PocketVault – USB‑Encrypted Password Manager

A Chrome extension that securely stores website credentials in an **AES‑256‑encrypted SQLite database** located on a **USB flash drive**, powered by a **FastAPI** backend.

---

## 📁 Project Structure

```
.
├── Basic_USB_interface.py       # USB operations and AES encryption logic
├── password_server.py           # FastAPI backend API
└── extension/
    ├── background.js            # Chrome service worker
    ├── content.js               # Autofill and capture scripts
    ├── manifest.json            # Chrome extension manifest (v3)
    ├── popup.html               # User interface for password manager
    └── popup.js                 # UI interaction logic
```

---

## 🚀 Getting Started

### 1. Start the Backend Server

Ensure your USB stick is plugged in and mounted.

```
pip install -r requirements.txt
```


```bash
pip install fastapi uvicorn cryptography psutil
uvicorn password_server:app --host 127.0.0.1 --port 5000
```

This launches the API at `http://127.0.0.1:5000`

---

### 2. Load the Chrome Extension

- Open `chrome://extensions/`
- Enable **Developer mode**
- Click **Load unpacked**
- Select the `/extension` folder

---

## 🧩 How It Works

1. The user sets a **master password** (passphrase) in the popup.
2. The passphrase is deterministically converted into a 256-bit AES key via PBKDF2.
3. Credentials are stored in an SQLite database on a USB drive.
4. The database is always encrypted (AES‑256‑CBC) except during brief decryption inside a temp file for operations.
5. The Chrome extension communicates with the FastAPI backend to save/retrieve credentials.

---

## 🔐 Security Details

- AES‑256‑CBC encryption with random IV
- PBKDF2-HMAC-SHA256 key derivation:
  ```python
  pbkdf2_hmac('sha256', password.encode(), salt=b'IL0V3EC52!', iterations=100000)
  ```
- USB paths auto-detected via `psutil`
- Passwords are never stored on disk unencrypted

---

## 🖥️ API Endpoints

| Endpoint              | Method | Description                         |
|-----------------------|--------|-------------------------------------|
| `/savePassword`       | POST   | Save or overwrite credentials       |
| `/getPassword/{site}` | GET    | Retrieve credentials for a website |
| `/importFromUSB`      | POST   | Import plaintext credentials list   |
| `/exportToUSB`        | GET    | Export stored credentials (text)    |
| `/setupUSB`           | POST   | Initialize and encrypt new database |
| `/encryptUSB`         | POST   | Encrypt existing database           |
| `/usbStatus`          | GET    | USB detection and status info       |

---

## 🧪 Extension Features

- Autofill login forms (username + password)
- Save credentials when user submits a form
- Manually view credentials from popup
- Toggle password visibility in input fields
- Secure local storage of master key (Chrome local storage)

---
## TODOs

 - [] Automatically clearing Master key or allow manually clearing it
 - [] Add Prompt for setup process
---

