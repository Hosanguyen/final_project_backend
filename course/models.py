from django.db import models
from django.utils import timezone

from users.models import User

# Create your models here.

class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=120, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.name
    
class Language(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    externalid = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="External ID for integration with DOMjudge")
    extension = models.CharField(max_length=50, null=True, blank=True, help_text="File extension for this language (e.g., .py, .java, .cpp)")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "languages"

    def __str__(self):
        return self.name
    
class File(models.Model):
    id = models.BigAutoField(primary_key=True)
    storage_key = models.FileField(upload_to='files/uploads/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "files"

    def __str__(self):
        return self.filename
    
    @property
    def file_url(self):
        if self.storage_key:
            return self.storage_key.url
        return None

class Course(models.Model):
    LEVEL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    id = models.BigAutoField(primary_key=True)
    slug = models.SlugField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=512, null=True, blank=True)
    long_description = models.TextField(null=True, blank=True)
    banner = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True, related_name="course_banners", help_text="Banner image for course")
    languages = models.ManyToManyField(Language, related_name="courses", blank=True)
    tags = models.ManyToManyField(Tag, related_name="courses", blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="beginner")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_courses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
            User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_courses"
        )

    class Meta:
        db_table = "courses"

    def __str__(self):
        return self.title

class Lesson(models.Model):
    id = models.BigAutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    sequence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lessons"
        ordering = ["sequence", "created_at"]

    def __str__(self):
        if self.course:
            return f"{self.title} ({self.course.title})"
        return self.title

class LessonResource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ("video", "Video"),
        ("pdf", "PDF"),
        ("slide", "Slide"),
        ("text", "Text"),
        ("link", "Link"),
        ("file", "File"),
    ]

    id = models.BigAutoField(primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    title = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True, related_name="resources")
    url = models.URLField(max_length=1024, null=True, blank=True)
    sequence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lesson_resources"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.type} - {self.title or self.lesson.title}"

class Enrollment(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrollments"
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} → {self.course}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="orders")
    order_code = models.CharField(max_length=50, unique=True, help_text="Mã đơn hàng duy nhất")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Số tiền thanh toán")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    # VNPay transaction info
    vnp_txn_ref = models.CharField(max_length=100, null=True, blank=True, help_text="Mã tham chiếu giao dịch VNPay")
    vnp_transaction_no = models.CharField(max_length=100, null=True, blank=True, help_text="Mã giao dịch tại VNPay")
    vnp_response_code = models.CharField(max_length=10, null=True, blank=True, help_text="Mã phản hồi từ VNPay")
    vnp_bank_code = models.CharField(max_length=20, null=True, blank=True, help_text="Mã ngân hàng")
    vnp_pay_date = models.CharField(max_length=14, null=True, blank=True, help_text="Thời gian thanh toán")
    
    # Additional info
    payment_method = models.CharField(max_length=50, default="vnpay", help_text="Phương thức thanh toán")
    metadata = models.JSONField(null=True, blank=True, help_text="Thông tin bổ sung")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, help_text="Thời gian hoàn thành thanh toán")

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_code} - {self.user.username} - {self.course.title}"


class LessonQuiz(models.Model):
    """Bảng trung gian giữa Lesson và Quiz"""
    id = models.BigAutoField(primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_quizzes")
    quiz = models.ForeignKey('quizzes.Quiz', on_delete=models.CASCADE, related_name="lesson_quizzes")
    sequence = models.IntegerField(default=0, verbose_name="Thứ tự quiz trong lesson")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_quizzes"
        verbose_name = "Lesson Quiz"
        verbose_name_plural = "Lesson Quizzes"
        ordering = ["lesson", "sequence"]
        unique_together = ("lesson", "quiz")

    def __str__(self):
        return f"{self.lesson.title} - Quiz: {self.quiz.title}"
