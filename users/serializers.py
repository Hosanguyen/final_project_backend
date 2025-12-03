from rest_framework import serializers
from .models import User, PermissionCategory, Permission, Role, UserRole, ContestRatingChange

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
        fields = ["old_password", "password", "password_confirm"]
    
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

# PERMISSION CATEGORY SERIALIZERS
class PermissionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionCategory
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PermissionCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionCategory
        fields = ["id", "name", "description"]


# PERMISSION SERIALIZERS

class PermissionSerializer(serializers.ModelSerializer):
    category = PermissionCategoryListSerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Permission
        fields = ["id", "code", "description", "category", "category_id", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def create(self, validated_data):
        category_id = validated_data.pop("category_id", None)
        permission = Permission.objects.create(**validated_data)
        if category_id:
            permission.category_id = category_id
            permission.save()
        return permission
    
    def update(self, instance, validated_data):
        category_id = validated_data.pop("category_id", None)
        instance.code = validated_data.get("code", instance.code)
        instance.description = validated_data.get("description", instance.description)
        if category_id is not None:
            instance.category_id = category_id
        instance.save()
        return instance


class PermissionListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    
    class Meta:
        model = Permission
        fields = ["id", "code", "description", "category_name"]


class PermissionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code"]


# ROLE SERIALIZERS

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionListSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "permission_count", "user_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def get_permission_count(self, obj):
        return obj.permissions.count()
    
    def get_user_count(self, obj):
        return obj.users.count()


class RoleListSerializer(serializers.ModelSerializer):
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ["id", "name", "description", "permission_count", "user_count"]
    
    def get_permission_count(self, obj):
        return obj.permissions.count()
    
    def get_user_count(self, obj):
        return obj.users.count()


class RoleSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Role
        fields = ["name", "description", "permission_ids"]
    
    def validate_permission_ids(self, value):
        if value:
            existing_count = Permission.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("Một số permission ID không tồn tại")
        return value
    
    def create(self, validated_data):
        permission_ids = validated_data.pop("permission_ids", [])
        role = Role.objects.create(**validated_data)
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
        return role
    
    def update(self, instance, validated_data):
        permission_ids = validated_data.pop("permission_ids", None)
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)
        return instance


# ROLE-PERMISSION MANAGEMENT

class AssignPermissionsToRoleSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    
    def validate_permission_ids(self, value):
        if not value:
            raise serializers.ValidationError("Danh sách permission IDs không được rỗng")
        existing_count = Permission.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Một số permission ID không tồn tại")
        return value


class RemovePermissionsFromRoleSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )



# USER-ROLE SERIALIZERS
class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    
    class Meta:
        model = UserRole
        fields = ["id", "user", "username", "role", "role_name", "assigned_at"]
        read_only_fields = ["id", "assigned_at"]


class AssignRolesToUserSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    
    def validate_role_ids(self, value):
        if not value:
            raise serializers.ValidationError("Danh sách role IDs không được rỗng")
        existing_count = Role.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Một số role ID không tồn tại")
        return value


class RemoveRolesFromUserSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )


# USER WITH ROLES

class UserWithRolesSerializer(serializers.ModelSerializer):
    roles = RoleSimpleSerializer(many=True, read_only=True)
    role_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "active", "roles", "role_count", "created_at"]
    
    def get_role_count(self, obj):
        return obj.roles.count()


class UserDetailWithPermissionsSerializer(serializers.ModelSerializer):
    roles = RoleListSerializer(many=True, read_only=True)
    all_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "active", "roles", "all_permissions", "created_at"]
    
    def get_all_permissions(self, obj):
        permissions = Permission.objects.filter(roles__users=obj).distinct()
        return PermissionSimpleSerializer(permissions, many=True).data


# ROLE WITH USERS

class RoleWithUsersSerializer(serializers.ModelSerializer):
    users = UserListSerializer(many=True, read_only=True)
    permissions = PermissionListSerializer(many=True, read_only=True)
    user_count = serializers.SerializerMethodField()
    permission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ["id", "name", "description", "users", "user_count", "permissions", "permission_count", "created_at"]
    
    def get_user_count(self, obj):
        return obj.users.count()
    
    def get_permission_count(self, obj):
        return obj.permissions.count()
    
class AssignRolesToUserSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    
    def validate_role_ids(self, value):
        if not value:
            raise serializers.ValidationError("Danh sách role IDs không được rỗng")
        existing_count = Role.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Một số role ID không tồn tại")
        return value


class RemoveRolesFromUserSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )


# ============= RATING SERIALIZERS =============

class UserRatingSerializer(serializers.ModelSerializer):
    """Serializer cho User rating information"""
    rank_color = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'avatar_url',
            'current_rating', 'max_rating', 'rank', 'max_rank', 'rank_color',
            'contests_participated', 'contests_won', 'total_problems_solved',
            'last_contest_at'
        ]
        read_only_fields = [
            'id', 'current_rating', 'max_rating', 'rank', 'max_rank',
            'contests_participated', 'contests_won', 'total_problems_solved',
            'last_contest_at'
        ]
    
    def get_rank_color(self, obj):
        return User.get_rank_color(obj.rank)


class UserRatingSimpleSerializer(serializers.ModelSerializer):
    """Serializer đơn giản cho rating trong user profile"""
    rank_color = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'current_rating', 'max_rating', 'rank', 'max_rank', 'rank_color',
            'contests_participated', 'total_problems_solved'
        ]
    
    def get_rank_color(self, obj):
        return User.get_rank_color(obj.rank)


class ContestRatingChangeSerializer(serializers.ModelSerializer):
    """Serializer cho lịch sử thay đổi rating"""
    contest_title = serializers.CharField(source='contest.title', read_only=True)
    contest_slug = serializers.CharField(source='contest.slug', read_only=True)
    rating_change_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestRatingChange
        fields = [
            'id', 'contest', 'contest_title', 'contest_slug',
            'old_rating', 'new_rating', 'rating_change', 'rating_change_display',
            'rank', 'solved_count', 'created_at'
        ]
        read_only_fields = [
            'id', 'old_rating', 'new_rating', 'rating_change',
            'rank', 'solved_count', 'created_at'
        ]
    
    def get_rating_change_display(self, obj):
        """Format rating change with + or - sign"""
        if obj.rating_change >= 0:
            return f"+{obj.rating_change}"
        return str(obj.rating_change)


class GlobalRankingSerializer(serializers.Serializer):
    """Serializer cho global ranking leaderboard"""
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    avatar_url = serializers.ImageField()
    current_rating = serializers.IntegerField()
    max_rating = serializers.IntegerField()
    rank_title = serializers.CharField()
    rank_color = serializers.CharField()
    contests_participated = serializers.IntegerField()
    contests_won = serializers.IntegerField()
    total_problems_solved = serializers.IntegerField()