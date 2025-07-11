from datetime import datetime, timedelta, timezone
import os
import secrets

import jwt

from src.lib.configuration import configuration
from src.lib.exception.exception_server import TokenException
from src.lib.utility.utils import IdentifiedUtils
from src.models.user.auth_model import UserToken



def get_path(public_key_path: str = 'public_key.pem'):
    path = os.path.join(os.path.dirname(__file__), public_key_path)
    project_root = os.path.dirname(os.path.abspath(__file__))
    return path, project_root


def read_public_key(public_key_path: str = 'public_key.pem') -> bytes:
    if public_key_path:
        path = os.path.join(os.path.dirname(__file__), public_key_path)
        print(f"Reading public key from: {path}")
        with open(path, "rb") as public_key_file:
            return public_key_file.read()
    return configuration.get_env_var("jwts.public.key")


def read_private_key(private_key_path: str = 'private_key.pem') -> bytes:
    if private_key_path:
        path = os.path.join(os.path.dirname(__file__), private_key_path)
        print(f"Reading private key from: {path}")
        with open(path, "rb") as private_key_file:
            return private_key_file.read()
    return configuration.get_env_var("jwts.private.key")


class TokenManager:
    algo: str = "RS256"
    secret_key: str = secrets.token_urlsafe(64)
    public_key: bytes = read_public_key()
    private_key: bytes = read_private_key()

    @classmethod
    def generate_token(
            cls,
            user_id: str,
            user_data: UserToken,
            session: str = IdentifiedUtils.get_unique_id(),
            hours: int = 12
    ) -> str:

        payload = {
            "sub": user_id,
            "user": user_data.to_json(),
            "session": session,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=hours)
        }

        token = jwt.encode(payload, cls.private_key, algorithm=cls.algo)
        return token

    @classmethod
    def decode_token(cls, token: str) -> UserToken:
        try:
            payload = jwt.decode(token, cls.public_key, algorithms=[cls.algo])
            return UserToken(**(payload["user"]))
        except jwt.DecodeError as e:
            print(e)
            raise TokenException("Token decoding error")
        except jwt.ExpiredSignatureError:
            raise TokenException("Token expired")
        except jwt.InvalidTokenError:
            raise TokenException("Invalid token")



