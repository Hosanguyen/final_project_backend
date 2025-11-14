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
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    sequence = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lessons"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.title} ({self.course.title})"

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
