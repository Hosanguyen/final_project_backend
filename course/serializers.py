from rest_framework import serializers
from .models import Language, Tag, File, Course, Lesson, LessonResource, Enrollment

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
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    lessons_count = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'slug', 'title', 'short_description', 'long_description',
            'languages', 'tags', 'level', 'price', 'is_published', 
            'published_at', 'created_by', 'created_by_name', 'created_at',
            'updated_at', 'updated_by', 'updated_by_name', 'language_ids',
            'tag_ids', 'lessons_count', 'enrollments_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'published_at']
    
    def get_lessons_count(self, obj):
        return obj.lessons.count()
    
    def get_enrollments_count(self, obj):
        return obj.enrollments.count()
    
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
            'id', 'type', 'title', 'content', 'file', 'url', 
            'sequence', 'created_at', 'updated_at', 'file_url', 'filename'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class LessonSerializer(serializers.ModelSerializer):
    resources = LessonResourceSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    resources_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'course', 'course_title', 'title', 'description', 
            'sequence', 'created_at', 'updated_at', 'resources', 'resources_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_resources_count(self, obj):
        return obj.resources.count()

class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'course', 'course_title', 'user_name',
            'enrolled_at', 'progress_percent', 'last_accessed_at'
        ]
        read_only_fields = ['id', 'enrolled_at']
