from django.db import models
from django.core.validators import MinValueValidator
from users.models import User
from course.models import Lesson


class Quiz(models.Model):
    """Bảng quizzes (Đề thi)"""
    title = models.CharField(max_length=255, verbose_name="Tiêu đề bài thi")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả bài thi")
    time_limit_seconds = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Thời gian làm bài (giây)"
    )
    is_published = models.BooleanField(default=False, verbose_name="Đã công khai")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_quizzes',
        verbose_name="Người tạo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    """Bảng quiz_questions (Câu hỏi)"""
    QUESTION_TYPE_SINGLE = 1  # 1 đáp án đúng
    QUESTION_TYPE_MULTIPLE = 2  # Nhiều đáp án đúng
    
    QUESTION_TYPE_CHOICES = [
        (QUESTION_TYPE_SINGLE, 'Single Choice'),
        (QUESTION_TYPE_MULTIPLE, 'Multiple Choice'),
    ]
    
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Quiz"
    )
    content = models.TextField(verbose_name="Nội dung câu hỏi")
    question_type = models.IntegerField(
        choices=QUESTION_TYPE_CHOICES,
        default=QUESTION_TYPE_SINGLE,
        verbose_name="Loại câu hỏi"
    )
    points = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name="Điểm"
    )
    sequence = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Thứ tự"
    )
    
    class Meta:
        db_table = 'quiz_questions'
        verbose_name = 'Quiz Question'
        verbose_name_plural = 'Quiz Questions'
        ordering = ['quiz', 'sequence']
        unique_together = ['quiz', 'sequence']
    
    def __str__(self):
        return f"Q{self.sequence}: {self.content[:50]}"


class QuizOption(models.Model):
    """Bảng quiz_options (Lựa chọn đáp án)"""
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name="Câu hỏi"
    )
    option_text = models.TextField(verbose_name="Nội dung đáp án")
    is_correct = models.BooleanField(default=False, verbose_name="Đáp án đúng")
    
    class Meta:
        db_table = 'quiz_options'
        verbose_name = 'Quiz Option'
        verbose_name_plural = 'Quiz Options'
    
    def __str__(self):
        return f"Option: {self.option_text[:30]}"


class QuizSubmission(models.Model):
    """Bảng quiz_submissions (Lượt làm bài)"""
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_SUBMITTED, 'Submitted'),
    ]
    
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name="Quiz"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quiz_submissions',
        verbose_name="Người làm bài"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quiz_submissions',
        verbose_name="Bài học",
        help_text="Bài học mà quiz này thuộc về (nếu có)"
    )
    total_score = models.FloatField(default=0, verbose_name="Tổng điểm")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
        verbose_name="Trạng thái"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Lưu snapshot bài quiz khi làm bài (để tránh thay đổi sau này ảnh hưởng kết quả)
    quiz_snapshot = models.JSONField(
        default=dict,
        verbose_name="Snapshot bài quiz",
        help_text="Lưu toàn bộ cấu trúc quiz tại thời điểm làm bài"
    )
    
    class Meta:
        db_table = 'quiz_submissions'
        verbose_name = 'Quiz Submission'
        verbose_name_plural = 'Quiz Submissions'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.status}"


class QuizAnswer(models.Model):
    """Bảng quiz_answers (Chi tiết câu trả lời)"""
    submission = models.ForeignKey(
        QuizSubmission,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="Submission"
    )
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="Câu hỏi"
    )
    selected_option = models.ForeignKey(
        QuizOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='answers',
        verbose_name="Đáp án đã chọn"
    )
    text_answer = models.TextField(
        null=True,
        blank=True,
        verbose_name="Câu trả lời tự luận"
    )
    points_awarded = models.FloatField(default=0, verbose_name="Điểm đạt được")
    
    class Meta:
        db_table = 'quiz_answers'
        verbose_name = 'Quiz Answer'
        verbose_name_plural = 'Quiz Answers'
    
    def __str__(self):
        return f"Answer for Q{self.question.sequence}"
