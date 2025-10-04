from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.utils import timezone
from datetime import datetime

from .models import User, RevokedToken
from .serializers import RegisterSerializer, LoginSerializer
from common.authentication import CustomJWTAuthentication


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({"user": serializer.data, "tokens": tokens}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # cập nhật last_login
        user.last_login_at = timezone.now()
        user.last_login_ip = request.META.get("REMOTE_ADDR")
        user.save(update_fields=["last_login_at", "last_login_ip"])

        tokens = get_tokens_for_user(user)
        return Response({"tokens": tokens})


class HelloAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]  
    permission_classes = [IsAuthenticated]  # bắt buộc phải có token

    def get(self, request):
        return Response({
            "message": f"Hello, {request.user.username}! Token của bạn hợp lệ."
        })

class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            
            access_token = str(refresh.access_token)
            jti = refresh.get('jti')

            if RevokedToken.objects.filter(jti=jti).exists():
                return Response(
                    {"detail": "This refresh token has been revoked"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            exp = refresh.get('exp')
            user_id = refresh.get('user_id')
            RevokedToken.objects.create(
                jti=jti,
                user_id=user_id,
                expires_at=datetime.fromtimestamp(exp)
            )
            user = User.objects.get(id=user_id)
            tokens = get_tokens_for_user(user)
            
            return Response({
                "tokens": tokens
            }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response(
                {"detail": "Token is invalid or expired"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            jti = refresh.get('jti')
            user_id = refresh.get('user_id')
            exp = refresh.get('exp')
            
            RevokedToken.objects.get_or_create(
                jti=jti,
                defaults={
                    'user_id': user_id,
                    'expires_at': datetime.fromtimestamp(exp)
                }
            )
            
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )