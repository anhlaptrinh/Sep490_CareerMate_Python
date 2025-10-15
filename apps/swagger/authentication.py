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

        if not auth_header:
            return None

        # Accept both 'Bearer <token>' and raw '<token>' header forms
        # Split on whitespace to safely extract the token part
        parts = auth_header.split()
        if len(parts) == 1:
            token = parts[0]
        elif len(parts) == 2:
            scheme, token_part = parts
            if scheme.lower() != 'bearer':
                # Not our scheme — leave other authenticators a chance
                return None
            token = token_part
        else:
            # Malformed header (too many spaces)
            raise exceptions.AuthenticationFailed('Invalid Authorization header format')

        # If token is bytes, try to decode it (be defensive about encoding)
        if isinstance(token, (bytes, bytearray)):
            try:
                token = token.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    token = token.decode('latin-1')
                except Exception:
                    raise exceptions.AuthenticationFailed('Invalid token encoding')

        # Strip surrounding quotes if someone accidentally sent a quoted token
        if (token.startswith("\'") and token.endswith("\'")) or (token.startswith('"') and token.endswith('"')):
            token = token[1:-1]

        # Handle python bytes repr like: b'eyJ...'
        if token.startswith("b'") and token.endswith("'"):
            token = token[2:-1]
        if token.startswith('b"') and token.endswith('"'):
            token = token[2:-1]

        # Reject tokens that contain whitespace — JWTs must not contain spaces
        if any(c.isspace() for c in token):
            raise exceptions.AuthenticationFailed('Invalid token format (contains whitespace)')

        # Quick structural check for JWT (must have two dots)
        if token.count('.') != 2:
            raise exceptions.AuthenticationFailed('Invalid token format (not a JWT)')

        # Finally validate/parse the JWT
        try:
            payload = jwt.decode(
                token,
                settings.SPRING_BOOT_JWT_SECRET,
                algorithms=["HS512"],
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as e:
            # Provide a clearer message for header/base64 errors
            msg = str(e)
            if 'Invalid header string' in msg or 'utf-8' in msg:
                raise exceptions.AuthenticationFailed('Invalid token: token header/payload is not valid UTF-8 (corrupted or malformed token)')
            raise exceptions.AuthenticationFailed(f"Invalid token: {e}")

        user_identifier = payload.get("sub") or "anonymous"
        user = _TokenUser(user_identifier)
        return (user, token)
