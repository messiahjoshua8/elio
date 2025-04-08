import json
import base64
import os
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def derive_key(password, salt):
    """Derive a key from a password and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_credentials(credentials_file, password):
    """Encrypt the credentials file with a password"""
    # Generate a random salt
    salt = os.urandom(16)
    
    # Derive a key from the password
    key = derive_key(password, salt)
    
    # Set up the encryption cipher
    f = Fernet(key)
    
    # Read and encrypt the credentials file
    with open(credentials_file, 'rb') as file:
        file_data = file.read()
    
    encrypted_data = f.encrypt(file_data)
    
    # Return everything encoded in base64 for easy environment variable storage
    return {
        'encrypted_credentials': base64.b64encode(encrypted_data).decode(),
        'encryption_salt': base64.b64encode(salt).decode(),
        'password': password  # NEVER store this - just returned for user setup
    }

if __name__ == "__main__":
    credentials_file = input("Enter path to your credentials file [astute-setting-453616-i4-1b42112072cf.json]: ")
    if not credentials_file:
        credentials_file = "astute-setting-453616-i4-1b42112072cf.json"
    
    password = getpass.getpass("Enter encryption password: ")
    
    result = encrypt_credentials(credentials_file, password)
    
    print("\n=== Environment Variables for Production ===")
    print(f"ENVIRONMENT=production")
    print(f"ENCRYPTED_GOOGLE_CREDENTIALS={result['encrypted_credentials']}")
    print(f"CREDENTIALS_ENCRYPTION_SALT={result['encryption_salt']}")
    print(f"CREDENTIALS_ENCRYPTION_KEY={result['password']}")
    
    print("\nKeep these values secure! The CREDENTIALS_ENCRYPTION_KEY should be stored in a secure vault.")
    print("You can set these as environment variables in your production environment.")