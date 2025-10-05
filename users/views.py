from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import datetime

from .models import User, RevokedToken
from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserListSerializer, 
    AdminUpdateUserSerializer, 
    UserProfileSerializer, 
    UserResetPasswordSerializer, 
    AvatarSerializer)
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
        if not user.active:
            return Response({"detail": "User is not active"}, status=status.HTTP_401_UNAUTHORIZED)
        # cập nhật last_login
        user.last_login_at = timezone.now()
        user.last_login_ip = request.META.get("REMOTE_ADDR")
        user.save(update_fields=["last_login_at", "last_login_ip"])
        full_name = user.full_name
        tokens = get_tokens_for_user(user)
        return Response({
            "tokens": tokens,
            "full_name": full_name})


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
        
class AdminCRUDUser(APIView):
    authentication_classes = [CustomJWTAuthentication]  
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({"user": serializer.data, "tokens": tokens}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        users = User.objects.all()
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, id):
        user = get_object_or_404(User, id=id)
        serializer = AdminUpdateUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "User updated successfully.", "user": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        user = get_object_or_404(User, id=id)
        username = user.username 
        user.delete()
        return Response(
            {"detail": f"User '{username}' deleted successfully."},
            status=status.HTTP_200_OK
        )

class UserProfileView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User updated successfully.", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserResetPasswordView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        serializer = UserResetPasswordSerializer(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

class UserAvatarView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        user = request.user
        if not user.avatar_url:
            return Response(
                {"detail": "User has no avatar to delete."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user.avatar_url.delete(save=False)
        except Exception as e:
            print(f"Error deleting avatar: {e}")
        user.avatar_url = None
        user.save(update_fields=["avatar_url"])
        return Response({"detail": "Avatar deleted successfully."}, status=status.HTTP_200_OK)
