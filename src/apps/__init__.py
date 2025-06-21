from functools import wraps

from flask import request, g

from src.lib.authentication.auth_token import TokenManager
from src.lib.exception.exception_server import TokenException, UnauthorizedException


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return {'error': 'Token is missing!'}, 401

        try:
            user = TokenManager.decode_token(token=token)

            if 'admin' in request.url and user.role != 'admin':
                raise UnauthorizedException('You are not authorized to perform this operation')

            g.user = user
        except TokenException as e:
            return {'error': str(e)}, 401

        return f(*args, **kwargs)

    return decorated

