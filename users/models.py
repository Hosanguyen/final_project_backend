from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    is_default = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    permissions = models.ManyToManyField("Permission", through="RolePermission", related_name="roles")

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class Permission(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True)  # e.g. "course.create"
    description = models.CharField(max_length=255, blank=True, null=True)
    model_name = models.CharField(max_length=255, null=True)
    perm = models.CharField(max_length=255, null=True) # create || read || update || delete
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey("PermissionCategory", on_delete=models.SET_NULL, blank=True, null=True, db_column="category_id")

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.code

class PermissionCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permission_categories"

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column="role_id")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, db_column="permission_id")

    class Meta:
        db_table = "role_permissions"
        unique_together = ("role", "permission")


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
    avatar_url = models.ImageField(upload_to="images/avatars/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)

    last_login_at = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    roles = models.ManyToManyField(Role, through="UserRole", related_name="users")

    # ============= RATING FIELDS =============
    RANK_CHOICES = [
        ('newbie', 'Newbie'),           # 0-1199
        ('pupil', 'Pupil'),             # 1200-1399
        ('specialist', 'Specialist'),   # 1400-1599
        ('expert', 'Expert'),           # 1600-1899
        ('candidate_master', 'Candidate Master'),  # 1900-2099
        ('master', 'Master'),           # 2100-2299
        ('international_master', 'International Master'),  # 2300-2399
        ('grandmaster', 'Grandmaster'), # 2400-2599
        ('international_grandmaster', 'International Grandmaster'),  # 2600-2999
        ('legendary_grandmaster', 'Legendary Grandmaster'),  # 3000+
    ]
    
    # Rating information
    current_rating = models.IntegerField(default=1500, help_text="Current rating của user")
    max_rating = models.IntegerField(default=1500, help_text="Rating cao nhất từng đạt được")
    rank = models.CharField(max_length=50, choices=RANK_CHOICES, default='specialist', help_text="Rank hiện tại dựa trên rating")
    max_rank = models.CharField(max_length=50, choices=RANK_CHOICES, default='specialist', help_text="Rank cao nhất từng đạt được")
    
    # Contest statistics
    contests_participated = models.IntegerField(default=0, help_text="Số contest đã tham gia")
    contests_won = models.IntegerField(default=0, help_text="Số contest đứng top 1")
    
    # Other stats
    total_problems_solved = models.IntegerField(default=0, help_text="Tổng số bài đã solve")
    rating_volatility = models.FloatField(default=350.0, help_text="Độ biến động rating (càng thi nhiều càng giảm)")
    
    # Rating timestamps
    last_contest_at = models.DateTimeField(null=True, blank=True, help_text="Thời điểm contest gần nhất")

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["-current_rating"]),
            models.Index(fields=["rank"]),
        ]

    def __str__(self):
        return self.full_name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_staff(self):
        if self.username == 'admin':
            return True
        return False

    def has_perm(self, role_name, perm_code):
        if not self.has_role(role_name):
            return False
        user_permissions = Permission.objects.filter(roles__users=self).values_list('code', flat=True)
        return perm_code in user_permissions
    
    def has_role(self, role_name):
        return self.roles.filter(name=role_name).exists()
    
    # ============= RATING METHODS =============
    @staticmethod
    def get_rank_from_rating(rating):
        """Determine rank based on rating"""
        if rating < 1200:
            return 'newbie'
        elif rating < 1400:
            return 'pupil'
        elif rating < 1600:
            return 'specialist'
        elif rating < 1900:
            return 'expert'
        elif rating < 2100:
            return 'candidate_master'
        elif rating < 2300:
            return 'master'
        elif rating < 2400:
            return 'international_master'
        elif rating < 2600:
            return 'grandmaster'
        elif rating < 3000:
            return 'international_grandmaster'
        else:
            return 'legendary_grandmaster'
    
    @staticmethod
    def get_rank_color(rank):
        """Get color for each rank (giống Codeforces)"""
        colors = {
            'newbie': '#808080',
            'pupil': '#008000',
            'specialist': '#03A89E',
            'expert': '#0000FF',
            'candidate_master': '#AA00AA',
            'master': '#FF8C00',
            'international_master': '#FF8C00',
            'grandmaster': '#FF0000',
            'international_grandmaster': '#FF0000',
            'legendary_grandmaster': '#FF0000',
        }
        return colors.get(rank, '#808080')
    
    def update_rank(self):
        """Update rank based on current rating"""
        self.rank = self.get_rank_from_rating(self.current_rating)
        if self.current_rating > self.get_rating_from_rank(self.max_rank):
            self.max_rank = self.rank
    
    @staticmethod
    def get_rating_from_rank(rank):
        """Get minimum rating for a rank"""
        ratings = {
            'newbie': 0,
            'pupil': 1200,
            'specialist': 1400,
            'expert': 1600,
            'candidate_master': 1900,
            'master': 2100,
            'international_master': 2300,
            'grandmaster': 2400,
            'international_grandmaster': 2600,
            'legendary_grandmaster': 3000,
        }
        return ratings.get(rank, 0)
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


# ============= RATING HISTORY MODEL =============

class ContestRatingChange(models.Model):
    """
    Model lưu lịch sử thay đổi rating sau mỗi contest
    """
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rating_changes')
    contest = models.ForeignKey('contests.Contest', on_delete=models.CASCADE, related_name='rating_changes')
    
    # Rating changes
    old_rating = models.IntegerField(help_text="Rating trước contest")
    new_rating = models.IntegerField(help_text="Rating sau contest")
    rating_change = models.IntegerField(help_text="Thay đổi rating (+/-)")
    
    # Contest performance
    rank = models.IntegerField(help_text="Thứ hạng trong contest")
    solved_count = models.IntegerField(help_text="Số bài solved")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "contest_rating_changes"
        unique_together = ("user", "contest")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["contest"]),
        ]
    
    def __str__(self):
        sign = '+' if self.rating_change >= 0 else ''
        return f"{self.user.username} - {self.contest.title}: {sign}{self.rating_change}"