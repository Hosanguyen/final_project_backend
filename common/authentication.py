from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework_simplejwt.tokens import AccessToken

from users.models import User

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token_str = auth_header.split(" ")[1]
        try:
            token = AccessToken(token_str)
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid token")

        user_id = token.get("user_id")
        if not user_id:
            raise exceptions.AuthenticationFailed("User not found")

        try:
            user = User.objects.get(id=user_id, active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found")

        return (user, token)
