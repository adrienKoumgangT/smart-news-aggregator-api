import os

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_key(folder_path: str = os.path.dirname(__file__)):

    # Generate private key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Save private key
    with open(os.path.join(folder_path, "private_key.pem"), "wb") as f:
        f.write(private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

    # Save public key
    with open(os.path.join(folder_path, "public_key.pem"), "wb") as f:
        f.write(private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ))


if __name__ == '__main__':
    generate_key()

