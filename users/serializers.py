from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "full_name"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]

class AdminUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "full_name", "avatar_url", "description", "dob", "gender", "phone", "address"]

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "avatar_url", "description", "dob", "gender", "phone", "address"]

class UserResetPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["password"]
    
    old_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError("Old password is incorrect")
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("New password and confirm password do not match")
        return attrs
    
    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save()
        return instance

class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["avatar_url"]
        extra_kwargs = {
            "avatar_url": {
                "required": False
            }
        }
    
    def update(self, instance, validated_data):
        old_avatar = instance.avatar_url
        if old_avatar and old_avatar != validated_data.get('avatar_url'):
            old_avatar.delete(save=False)
        instance.avatar_url = validated_data.get('avatar_url', instance.avatar_url)
        instance.save()
        return instance