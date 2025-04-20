import os
import psutil
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import sqlite3
import getpass
from hashlib import pbkdf2_hmac
import base64

def find_usb_drive():
    """Return the mount point of the first removable USB drive.

    On macOS and most Linux distros external volumes appear under /Volumes,
    /media/<user>, or /run/media/<user>.  On Windows we look for partitions
    whose options include the string "removable" (psutil sets this flag on
    USB sticks).  System volumes such as Recovery or Preboot are skipped.
    """
    partitions = psutil.disk_partitions()

    if os.name == "nt":  # Windows
        for p in partitions:
            if 'removable' in p.opts.lower():
                return p.mountpoint
    else:  # POSIX (macOS, Linux, etc.)
        for p in partitions:
            mnt = p.mountpoint
            if (
                (mnt.startswith('/Volumes/') or mnt.startswith('/media/') or mnt.startswith('/run/media/'))
                and 'Recovery' not in mnt
                and 'Preboot' not in mnt
            ):
                return mnt

    return None

def create_database(usb_path):
    """Ensure a passwords.db SQLite database exists on the USB drive.

    The database contains a single table `credentials`
    with columns: id, url, username, password.
    """
    db_path = os.path.join(usb_path, 'passwords.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        );
        '''
    )
    conn.commit()
    conn.close()
    print(f"'passwords.db' ready at: {db_path}")

def check_if_database_exists(usb_path):
    """
    Check whether the `passwords.db` database already exists on the USB drive.
    
    Returns
    -------
    str
        "database already exists"   – if the file is present  
        "database doesn't exist"    – if the file is not present
    """
    db_path = os.path.join(usb_path, 'passwords.db')
    if os.path.exists(db_path):
        return "database already exists"
    else:
        return "database doesn't exist"

def add_credentials(usb_path, url, username, password):
    """Insert a new credential row into the credentials table."""
    db_path = os.path.join(usb_path, 'passwords.db')

    # Ensure the database and table exist
    if not os.path.exists(db_path):
        create_database(usb_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT EXISTS(SELECT 1 FROM credentials WHERE url=? AND username=?)", (url, username))
    exists = cursor.fetchone()[0]
    
    if exists:
        print(f"Credentials already exist for {username} @ {url}.")
        return
    else:
        # Insert a brand‑new row
        cursor.execute(
            "INSERT INTO credentials (url, username, password) VALUES (?, ?, ?)",
            (url, username, password)
        )
        conn.commit()
        conn.close()
        print(f"Credentials added for {username} @ {url}")
        
def overwrite_credentials(usb_path, url, username, password):
    """Overwrite an existing credential for the given URL and username."""
    db_path = os.path.join(usb_path, 'passwords.db')
    if not os.path.exists(db_path):
        print("passwords.db not found. Cannot overwrite.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE credentials SET password = ? WHERE url = ? AND username = ?",
        (password, url, username)
    )
    conn.commit()
    conn.close()
    print(f"Credentials updated for {username} @ {url}")


def show_credentials(usb_path):
    """Print all rows in the credentials table."""
    db_path = os.path.join(usb_path, 'passwords.db')
    if not os.path.exists(db_path):
        print("passwords.db not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, username, password FROM credentials")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        print("\nStored credentials:")
        print("-" * 50)
        for i, (url, user, pwd) in enumerate(rows, 1):
            print(f"{i}. URL: {url}\n   Username: {user}\n   Password: {pwd}\n")
    else:
        print("No credentials stored.")

def encrypt_file(file_path, key):
    """Encrypt the database file using AES‑256‑CBC with PKCS7 padding.

    A fresh 16‑byte IV is generated and prepended to the ciphertext.
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes (256 bits).")

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()

    with open(file_path, 'rb') as f:
        plaintext = f.read()

    padded = padder.update(plaintext) + padder.finalize()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    with open(file_path, 'wb') as f:
        f.write(iv + ciphertext)

def decrypt_file(file_path, key):
    """Decrypt the AES‑256‑CBC encrypted database file."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes (256 bits).")

    with open(file_path, 'rb') as f:
        data = f.read()

    iv, ciphertext = data[:16], data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plain = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plain) + unpadder.finalize()

    with open(file_path, 'wb') as f:
        f.write(plaintext)

def main():
    print("Choose an option:")
    print("1. Setup")
    print("2. Run")
    print("3. Add credentials (test)")
    print("4. View credentials")
    user_choice = input("Enter 1, 2, 3 or 4: ").strip()

    if user_choice == '1':
        # Setup: Check for USB drive and create the passwords.db file
        usb_path = find_usb_drive()
        if usb_path:
            print(f"USB Drive found at: {usb_path}")
            create_database(usb_path)
            
            # Ask the user for an AES key or create one
            key_hex = getpass.getpass("Enter a 64‑hex‑character AES‑256 key (leave blank to generate one): ").strip()
            if key_hex == "":
                key = os.urandom(32)
                print(f"Generated key (save this safely!): {key.hex()}")
            else:
                try:
                    key = bytes.fromhex(key_hex)
                    if len(key) != 32:
                        raise ValueError
                except ValueError:
                    print("Invalid key. It must be exactly 64 hexadecimal characters.")
                    return

            file_path = os.path.join(usb_path, 'passwords.db')
            encrypt_file(file_path, key)
            
        else:
            print("No USB drive found")
    
    elif user_choice == '3':
        # Test flow: add a credential via user input
        usb_path = find_usb_drive()
        if usb_path:
            file_path = os.path.join(usb_path, 'passwords.db')
            if not os.path.exists(file_path):
                print("passwords.db does not exist on the USB drive. Please run Setup first.")
            else:
                key_hex = getpass.getpass("Enter the 64‑hex‑character AES key: ").strip()
                try:
                    key_input = bytes.fromhex(key_hex)
                    if len(key_input) != 32:
                        raise ValueError
                except ValueError:
                    print("Invalid key format.")
                    return

                try:
                    decrypt_file(file_path, key_input)
                    print("Database decrypted.")
                    
                    url = input("Enter the site URL: ").strip()
                    username = input("Enter the username: ").strip()
                    password = getpass.getpass("Enter the password: ")
                    
                    add_credentials(usb_path, url, username, password)
                    print("Credential added.")
                    
                    encrypt_file(file_path, key_input)
                    print("Database re‑encrypted. Test complete.")
                except Exception as e:
                    print(f"Decryption failed: {e}")
    
    elif user_choice == '4':
        # View credentials
        usb_path = find_usb_drive()
        if usb_path:
            file_path = os.path.join(usb_path, 'passwords.db')
            if not os.path.exists(file_path):
                print("passwords.db does not exist on the USB drive. Please run Setup first.")
            else:
                key_hex = getpass.getpass("Enter the 64‑hex‑character AES key: ").strip()
                try:
                    key_input = bytes.fromhex(key_hex)
                    if len(key_input) != 32:
                        raise ValueError
                except ValueError:
                    print("Invalid key format.")
                    return

                try:
                    decrypt_file(file_path, key_input)
                    print("Database decrypted.\n")
                    show_credentials(usb_path)
                    encrypt_file(file_path, key_input)
                    print("Database re‑encrypted.")
                except Exception as e:
                    print(f"Decryption failed: {e}")
        else:
            print("No USB drive found")
    
    elif user_choice == '2':
        # Run: Accept a symmetric key and decrypt the file
        key_hex = getpass.getpass("Enter the 64‑hex‑character AES key: ").strip()
        try:
            key_input = bytes.fromhex(key_hex)
            if len(key_input) != 32:
                raise ValueError
        except ValueError:
            print("Invalid key format.")
            return
            
        usb_path = find_usb_drive()
        if usb_path:
            file_path = os.path.join(usb_path, 'passwords.db')
            if os.path.exists(file_path):
                decrypt_file(file_path, key_input)
                print("File decrypted successfully.")
                
                # Keep running until user presses 'x'
                while True:
                    action = input("Press 'x' to re-encrypt and exit, or any key to keep the file decrypted: ").strip().lower()
                    if action == 'x':
                        encrypt_file(file_path, key_input)
                        print(f"File encrypted again. Program will now exit.")
                        break
            else:
                print("passwords.db does not exist on the USB drive.")
        else:
            print("No USB drive found")
    
    else:
        print("Invalid choice. Please select 1, 2, 3 or 4.")

    


def derive_aes_key(password: str, length: int = 32, iterations: int = 100_000) -> str:
    """
    Derive an AES key from a password for communication between frontend and backend
    This makes the same password always generate the same key.
    """
    salt = b'IL0V3EC52!'  
    key = pbkdf2_hmac(
        hash_name='sha256',
        password=password.encode(),
        salt=salt,
        iterations=iterations,
        dklen=length
    )
    # return base64.urlsafe_b64encode(key).decode()
    return key.hex()

if __name__ == '__main__':
    main()