from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from .serializers import LoginSerializer
from rest_framework.permissions import IsAuthenticated

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "username": user.username,
                "email": user.email
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class HelloAPIView(APIView):
    permission_classes = [IsAuthenticated]  # bắt buộc phải có token

    def get(self, request):
        return Response({
            "message": f"Hello, {request.user.username}! Token của bạn hợp lệ."
        })
