import os
import psutil
from cryptography.fernet import Fernet

def find_usb_drive():
    """Find the first mounted USB drive, excluding system volumes."""
    partitions = psutil.disk_partitions()
    for partition in partitions:
        # Check if the mountpoint starts with /Volumes and ensure it isn't a system volume like Recovery
        if partition.mountpoint.startswith('/Volumes/'):
            # Ignore system partitions (like Recovery, Preboot, etc.)
            if 'Recovery' not in partition.mountpoint and 'Preboot' not in partition.mountpoint:
                return partition.mountpoint
    return None

def create_password_file(usb_path):
    """Ensure a passwords.txt file exists on the USB drive.

    The function simply creates an empty file if one is not already present.
    """
    file_path = os.path.join(usb_path, 'passwords.txt')

    # If the file doesn't exist, create it
    if not os.path.exists(file_path):
        try:
            # Create an empty file
            with open(file_path, 'w'):
                pass
            print(f"'passwords.txt' created at: {file_path}")
        except Exception as e:
            print(f"An error occurred while creating passwords.txt: {e}")
    else:
        print("'passwords.txt' already exists.")

def add_credentials(usb_path, username, password):
    """Append a username/password pair to passwords.txt on the USB drive.

    The entry is written as: <username> : <password>
    """
    file_path = os.path.join(usb_path, 'passwords.txt')

    # Make sure the file exists
    if not os.path.exists(file_path):
        create_password_file(usb_path)

    # Append the new credentials
    with open(file_path, 'a') as file:
        file.write(f"{username} : {password}\n")

def encrypt_file(file_path, key):
    """Encrypt the passwords.txt file using Fernet symmetric encryption."""
    fernet = Fernet(key)
    
    # Read the file's contents
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    # Encrypt the data
    encrypted_data = fernet.encrypt(file_data)
    
    # Write the encrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(file_path, key):
    """Decrypt the passwords.txt file using the provided symmetric key."""
    fernet = Fernet(key)
    
    # Read the encrypted file's contents
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()
    
    # Decrypt the data
    decrypted_data = fernet.decrypt(encrypted_data)
    
    # Write the decrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(decrypted_data)

def generate_symmetric_key():
    """Generate a symmetric key for encryption and decryption."""
    key = Fernet.generate_key()
    print(f"Symmetric Key (Save this for later): {key.decode()}")
    return key

def main():
    print("Choose an option:")
    print("1. Setup")
    print("2. Run")
    user_choice = input("Enter 1 or 2: ").strip()

    if user_choice == '1':
        # Setup: Check for USB drive and create the passwords.txt file
        usb_path = find_usb_drive()
        if usb_path:
            print(f"USB Drive found at: {usb_path}")
            create_password_file(usb_path)
            
            # Encrypt the file using a symmetric key
            key = generate_symmetric_key()
            file_path = os.path.join(usb_path, 'passwords.txt')
            encrypt_file(file_path, key)
            
        else:
            print("No USB drive found")
    
    elif user_choice == '2':
        # Run: Accept a symmetric key and decrypt the file
        key_input = input("Enter the symmetric key for decryption: ").encode()
        usb_path = find_usb_drive()
        if usb_path:
            file_path = os.path.join(usb_path, 'passwords.txt')
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
                print("passwords.txt does not exist on the USB drive.")
        else:
            print("No USB drive found")
    
    else:
        print("Invalid choice. Please select either 1 or 2.")

if __name__ == '__main__':
    main()