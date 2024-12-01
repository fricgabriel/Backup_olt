from cryptography.fernet import Fernet

with open("fernet_key.txt", "rb") as key_file:
    key = key_file.read()

cipher_suite = Fernet(key)

username = '' # Usuário
password = '' # Senha 

encrypted_username = cipher_suite.encrypt(username.encode())
encrypted_password = cipher_suite.encrypt(password.encode())

with open("credentials.py", "w") as cred_file:
    cred_file.write(f"encrypted_username = {encrypted_username}\n")
    cred_file.write(f"encrypted_password = {encrypted_password}\n")
