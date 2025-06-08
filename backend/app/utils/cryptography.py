import base64
import secrets
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Cryptographer:
    def __init__(self):
        self.kdf_algortihm = hashes.SHA256()
        self.kdf_length = 32
        self.kdf_iterations = 1000 #This is min recommended total count of iteration as mentioned in rfc8018 section-4.2

    def encrypt(self, plaintext: str, password: str) -> Tuple[bytes,bytes]:
        salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=self.kdf_algortihm,
            length=self.kdf_length,
            iterations=self.kdf_iterations,
            salt=salt
        )

        key = kdf.derive(password.encode("utf-8"))
        f = Fernet(base64.urlsafe_b64encode(key))

        ciphertext = f.encrypt(plaintext.encode("utf-8"))

        return ciphertext, salt
    
    def decrypt(self,ciphertext: bytes, password: str, salt: bytes) -> str:
        kdf = PBKDF2HMAC(
            algorithm=self.kdf_algortihm, length=self.kdf_length, salt=salt,
            iterations=self.kdf_iterations)
        key = kdf.derive(password.encode("utf-8"))

        f = Fernet(base64.urlsafe_b64encode(key))
        plaintext = f.decrypt(ciphertext)

        return plaintext.decode("utf-8")