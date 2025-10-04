from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import User
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
