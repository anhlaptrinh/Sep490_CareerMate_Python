import jwt
from rest_framework import authentication, exceptions
from django.conf import settings


class _TokenUser:
    def __init__(self, identifier):
        self.identifier = identifier

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return str(self.identifier)


class BearerAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        # TODO: Use the following line in production
        # if not auth_header or not auth_header.startswith('Bearer '):
        #     return None
        #
        # token = auth_header.replace('Bearer ', '').strip()

        if not auth_header:
            return None
        token = auth_header.strip()

        try:
            payload = jwt.decode(
                token,
                settings.SPRING_BOOT_JWT_SECRET,
                algorithms=["HS512"]
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {e}")

        user_identifier = payload.get("sub") or "anonymous"
        user = _TokenUser(user_identifier)
        return (user, token)
