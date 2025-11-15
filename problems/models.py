from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User
from course.models import Tag, File, Language


class Problem(models.Model):
    """Problem - Lưu ở cả Django DB và DOMjudge"""
    
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    id = models.BigAutoField(primary_key=True)
    slug = models.SlugField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    
    # Đề bài (cho frontend)
    short_statement = models.CharField(max_length=512, null=True, blank=True)
    statement_text = models.TextField(help_text="Full problem description (HTML)")
    
    # Input/Output format (text - cho frontend)
    input_format = models.TextField(null=True, blank=True)
    output_format = models.TextField(null=True, blank=True)
    
    # Constraints
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="medium")
    time_limit_ms = models.IntegerField(
        default=1000, 
        validators=[MinValueValidator(100), MaxValueValidator(30000)]
    )
    memory_limit_kb = models.IntegerField(
        default=262144, 
        validators=[MinValueValidator(1024), MaxValueValidator(2097152)]
    )
    
    # Metadata
    source = models.CharField(max_length=255, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    
    # Editorial
    editorial_text = models.TextField(null=True, blank=True, help_text="Lời giải (HTML)")
    editorial_file = models.ForeignKey(
        File, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="problem_editorials"
    )
    
    # DOMjudge Integration
    domjudge_problem_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="ID của problem trong DOMjudge (sau khi sync)"
    )
    is_synced_to_domjudge = models.BooleanField(
        default=False,
        help_text="Đã đồng bộ lên DOMjudge chưa"
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    # Relationships
    tags = models.ManyToManyField(Tag, through="TagProblem", related_name="problems", blank=True)
    allowed_languages = models.ManyToManyField(Language, related_name="allowed_problems", blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_problems")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_problems")

    class Meta:
        db_table = "problems"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class TagProblem(models.Model):
    id = models.BigAutoField(primary_key=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, db_column="tag_id")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, db_column="problem_id")

    class Meta:
        db_table = "tags_problems"
        unique_together = ("tag", "problem")


class TestCase(models.Model):
    """Test case - Lưu cả TEXT (hiển thị) và FILE (upload DOMjudge)"""
    
    TEST_TYPE_CHOICES = [
        ("sample", "Sample"),   # Public
        ("secret", "Secret"),   # Hidden
    ]

    id = models.BigAutoField(primary_key=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="test_cases")
    
    type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES, default="secret")
    sequence = models.IntegerField(default=0)
    
    # === TEXT (để hiển thị trên frontend) ===
    input_data = models.TextField(help_text="Input data (text)")
    output_data = models.TextField(help_text="Expected output (text)")
    
    # === FILE (để upload lên DOMjudge) ===
    # Tự động tạo file từ text khi sync
    input_file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_inputs",
        help_text="File đầu vào (tự động tạo khi sync)"
    )
    output_file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_outputs",
        help_text="File đầu ra (tự động tạo khi sync)"
    )
    
    # Override limits
    time_limit_ms = models.IntegerField(null=True, blank=True)
    memory_limit_kb = models.IntegerField(null=True, blank=True)
    
    # Scoring
    points = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_cases"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.problem.title} - Test #{self.sequence}"

class Submissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, related_name="submissions")
    code_file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, related_name="submissions")
    code_text = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    domjudge_submission_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "submissions"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Submission #{self.id} by {self.user.username} for {self.problem.title}"