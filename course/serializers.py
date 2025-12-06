from rest_framework import serializers
from .models import Language, Tag, File, Course, Lesson, LessonResource, Enrollment, Order
from .models import Language, Tag, File, Course, Lesson, LessonResource, Enrollment, LessonQuiz

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"

class FileSerializer(serializers.ModelSerializer):
    file_url = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = "__all__"

class CourseSerializer(serializers.ModelSerializer):
    languages = LanguageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    language_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False
    )
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_full_name = serializers.SerializerMethodField()
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    lessons_count = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'slug', 'title', 'short_description', 'long_description',
            'languages', 'tags', 'level', 'price', 'is_published', 
            'published_at', 'created_by', 'created_by_name', 'created_by_full_name',
            'created_at', 'updated_at', 'updated_by', 'updated_by_name', 'language_ids',
            'tag_ids', 'lessons_count', 'enrollments_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'published_at']
    
    def get_lessons_count(self, obj):
        return obj.lessons.count()
    
    def get_enrollments_count(self, obj):
        return obj.enrollments.count()
    
    def get_created_by_full_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.username
        return None
    
    def create(self, validated_data):
        language_ids = validated_data.pop('language_ids', [])
        tag_ids = validated_data.pop('tag_ids', [])
        
        course = Course.objects.create(**validated_data)
        
        if language_ids:
            course.languages.set(language_ids)
        if tag_ids:
            course.tags.set(tag_ids)
            
        return course
    
    def update(self, instance, validated_data):
        language_ids = validated_data.pop('language_ids', None)
        tag_ids = validated_data.pop('tag_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if language_ids is not None:
            instance.languages.set(language_ids)
        if tag_ids is not None:
            instance.tags.set(tag_ids)
            
        return instance

class LessonResourceSerializer(serializers.ModelSerializer):
    file_url = serializers.CharField(source='file.file_url', read_only=True)
    filename = serializers.CharField(source='file.filename', read_only=True)
    
    class Meta:
        model = LessonResource
        fields = [
            'id', 'lesson', 'type', 'title', 'content', 'file', 'url', 
            'sequence', 'created_at', 'updated_at', 'file_url', 'filename'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class LessonQuizSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_description = serializers.CharField(source='quiz.description', read_only=True)
    quiz_time_limit = serializers.IntegerField(source='quiz.time_limit_seconds', read_only=True)
    
    class Meta:
        model = LessonQuiz
        fields = ['id', 'lesson', 'quiz', 'quiz_title', 'quiz_description', 'quiz_time_limit', 'sequence', 'created_at']
        read_only_fields = ['id', 'created_at']

class LessonSerializer(serializers.ModelSerializer):
    resources = LessonResourceSerializer(many=True, read_only=True)
    quizzes = LessonQuizSerializer(source='lesson_quizzes', many=True, read_only=True)
    course_title = serializers.SerializerMethodField()
    resources_count = serializers.SerializerMethodField()
    quizzes_count = serializers.SerializerMethodField()
    quiz_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="Danh sách ID của các quiz đã có"
    )
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'course_title', 'title', 'description', 
            'sequence', 'created_at', 'updated_at', 'resources', 'resources_count',
            'quizzes', 'quizzes_count', 'quiz_ids'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_course_title(self, obj):
        return obj.course.title if obj.course else None
    
    def get_resources_count(self, obj):
        return obj.resources.count()
    
    def get_quizzes_count(self, obj):
        return obj.lesson_quizzes.count()
    
    def create(self, validated_data):
        quiz_ids = validated_data.pop('quiz_ids', [])
        lesson = Lesson.objects.create(**validated_data)
        
        # Tạo LessonQuiz cho các quiz được chọn
        if quiz_ids:
            for index, quiz_id in enumerate(quiz_ids):
                LessonQuiz.objects.create(
                    lesson=lesson,
                    quiz_id=quiz_id,
                    sequence=index + 1
                )
        
        return lesson
    
    def update(self, instance, validated_data):
        quiz_ids = validated_data.pop('quiz_ids', None)
        
        # Cập nhật các trường cơ bản
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Cập nhật quizzes nếu có
        if quiz_ids is not None:
            # Xóa tất cả LessonQuiz cũ
            instance.lesson_quizzes.all().delete()
            
            # Tạo LessonQuiz mới
            for index, quiz_id in enumerate(quiz_ids):
                LessonQuiz.objects.create(
                    lesson=instance,
                    quiz_id=quiz_id,
                    sequence=index + 1
                )
        
        return instance

class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'course', 'course_title', 'user_name',
            'enrolled_at', 'progress_percent', 'last_accessed_at'
        ]
        read_only_fields = ['id', 'enrolled_at']


class OrderSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_slug = serializers.CharField(source='course.slug', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'course', 'order_code', 'amount', 'status',
            'vnp_txn_ref', 'vnp_transaction_no', 'vnp_response_code',
            'vnp_bank_code', 'vnp_pay_date', 'payment_method', 'metadata',
            'created_at', 'updated_at', 'completed_at',
            'course_title', 'course_slug', 'user_name', 'user_email'
        ]
        read_only_fields = [
            'id', 'order_code', 'vnp_txn_ref', 'vnp_transaction_no',
            'vnp_response_code', 'vnp_bank_code', 'vnp_pay_date',
            'created_at', 'updated_at', 'completed_at'
        ]

