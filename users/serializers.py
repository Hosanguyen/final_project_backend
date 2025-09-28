from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()  # luôn dùng get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Sai tài khoản hoặc mật khẩu")
        data['user'] = user
        return data
