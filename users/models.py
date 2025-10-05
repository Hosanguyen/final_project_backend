from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class Permission(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True)  # e.g. "course.create"
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column="role_id")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, db_column="permission_id")

    class Meta:
        db_table = "role_permissions"
        unique_together = ("role", "permission")


class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=120, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.name


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    # profile optional
    full_name = models.CharField(max_length=200, blank=True, null=True)
    avatar_url = models.ImageField(upload_to="static/images/avatars/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)

    last_login_at = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    roles = models.ManyToManyField(Role, through="UserRole", related_name="users")

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.full_name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    @property
    def is_authenticated(self):
        return True

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column="role_id")
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user_roles"
        unique_together = ("user", "role")

class RevokedToken(models.Model):
    jti = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    revoked_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = "revoked_tokens"