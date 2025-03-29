# EC521_final_proj

GPT suggested me this project structure.

```
usb_password_manager/
├── app.py                    # Flask web API for browser extension
├── vault.txt                 # Encrypted password entries (TXT)
├── salt.bin                  # Salt used for key derivation
├── check.bin                 # Encrypted check string for master password validation
├── utils/                    # Core encryption and storage logic
│   ├── __init__.py           # Marks the directory as a Python package
│   ├── crypto_utils.py       # Key derivation, encryption, decryption
│   ├── storage_txt.py        # Read/write/search encrypted records in vault.txt
│   ├── auth.py               # Master password validation
└── extension/                # (Optional) Your browser extension code
    ├── manifest.json         # Chrome extension manifest
    ├── background.js         # Handles messaging + fills form
    ├── content.js            # Injected into pages to detect form fields
    └── popup.html/js         # Optional popup interface
```
## Notes

`Setup.py` should be run only once for initialization.

Not yet testable

Now the `utils` part is working.

The `app.py` is not complete.

The `extension` is empty.

Once the app.py is completed, the branch should be testable by sending  requests (GET, POST, etc.)

## Dependencies

Run ```conda env create -f environment.yml``` for conda, ```pip install -r requirements.txt``` for pip.

## TODO

 - [ ] Use database instead of .txt files.
