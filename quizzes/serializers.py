from rest_framework import serializers
from .models import Quiz, QuizQuestion, QuizOption, QuizSubmission, QuizAnswer
from users.serializers import UserListSerializer


# ============================================================
# QUIZ OPTION SERIALIZERS
# ============================================================

class QuizOptionSerializer(serializers.ModelSerializer):
    """Serializer cho Quiz Option (đọc)"""
    class Meta:
        model = QuizOption
        fields = ['id', 'option_text', 'is_correct']


class QuizOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer để tạo/cập nhật Option"""
    class Meta:
        model = QuizOption
        fields = ['option_text', 'is_correct']


# ============================================================
# QUIZ QUESTION SERIALIZERS
# ============================================================

class QuizQuestionSerializer(serializers.ModelSerializer):
    """Serializer cho Quiz Question (đọc)"""
    options = QuizOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizQuestion
        fields = ['id', 'content', 'question_type', 'points', 'sequence', 'options']


class QuizQuestionCreateSerializer(serializers.Serializer):
    """Serializer để tạo/cập nhật Question với Options"""
    id = serializers.IntegerField(required=False, allow_null=True)
    content = serializers.CharField()
    question_type = serializers.IntegerField()
    points = serializers.FloatField(min_value=0)
    sequence = serializers.IntegerField(min_value=1)
    options = QuizOptionCreateSerializer(many=True)
    
    def validate_question_type(self, value):
        if value not in [QuizQuestion.QUESTION_TYPE_SINGLE, QuizQuestion.QUESTION_TYPE_MULTIPLE]:
            raise serializers.ValidationError("Invalid question type")
        return value
    
    def validate_options(self, value):
        if not value or len(value) < 2:
            raise serializers.ValidationError("Question must have at least 2 options")
        
        correct_count = sum(1 for opt in value if opt.get('is_correct'))
        if correct_count == 0:
            raise serializers.ValidationError("Question must have at least 1 correct option")
        
        return value


# ============================================================
# QUIZ SERIALIZERS
# ============================================================

class QuizListSerializer(serializers.ModelSerializer):
    """Serializer cho danh sách Quiz"""
    created_by = UserListSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'time_limit_seconds',
            'is_published', 'created_by', 'created_at', 'updated_at',
            'question_count', 'total_points'
        ]
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
    def get_total_points(self, obj):
        return sum(q.points for q in obj.questions.all())


class QuizDetailSerializer(serializers.ModelSerializer):
    """Serializer chi tiết Quiz (bao gồm questions)"""
    created_by = UserListSerializer(read_only=True)
    questions = QuizQuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'time_limit_seconds',
            'is_published', 'created_by', 'created_at', 'updated_at',
            'questions', 'question_count', 'total_points'
        ]
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
    def get_total_points(self, obj):
        return sum(q.points for q in obj.questions.all())


class QuizCreateSerializer(serializers.ModelSerializer):
    """Serializer để tạo Quiz với Questions"""
    questions = QuizQuestionCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'time_limit_seconds',
            'is_published', 'questions'
        ]
    
    def validate_questions(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("Quiz must have at least 1 question")
        
        # Validate unique sequences
        sequences = [q['sequence'] for q in value]
        if len(sequences) != len(set(sequences)):
            raise serializers.ValidationError("Question sequences must be unique")
        
        return value
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        
        # Tạo Quiz
        quiz = Quiz.objects.create(**validated_data)
        
        # Tạo Questions và Options
        for q_data in questions_data:
            options_data = q_data.pop('options')
            
            question = QuizQuestion.objects.create(
                quiz=quiz,
                content=q_data['content'],
                question_type=q_data['question_type'],
                points=q_data['points'],
                sequence=q_data['sequence']
            )
            
            # Tạo Options
            for opt_data in options_data:
                QuizOption.objects.create(
                    question=question,
                    option_text=opt_data['option_text'],
                    is_correct=opt_data['is_correct']
                )
        
        return quiz


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Serializer để update Quiz (hỗ trợ thêm/sửa/xóa questions)"""
    questions = QuizQuestionCreateSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'time_limit_seconds',
            'is_published', 'questions'
        ]
    
    def validate_questions(self, value):
        if value is not None and len(value) > 0:
            # Validate unique sequences
            sequences = [q['sequence'] for q in value]
            if len(sequences) != len(set(sequences)):
                raise serializers.ValidationError("Question sequences must be unique")
        
        return value
    
    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        
        # Update Quiz fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update Questions nếu có
        if questions_data is not None:
            # XÓA tất cả questions cũ (cascade sẽ xóa options)
            instance.questions.all().delete()
            
            # TẠO LẠI questions mới
            for q_data in questions_data:
                options_data = q_data.pop('options')
                question_id = q_data.pop('id', None)
                
                question = QuizQuestion.objects.create(
                    quiz=instance,
                    content=q_data['content'],
                    question_type=q_data['question_type'],
                    points=q_data['points'],
                    sequence=q_data['sequence']
                )
                
                # Tạo Options
                for opt_data in options_data:
                    QuizOption.objects.create(
                        question=question,
                        option_text=opt_data['option_text'],
                        is_correct=opt_data['is_correct']
                    )
        
        return instance


# ============================================================
# QUIZ SUBMISSION & ANSWER SERIALIZERS
# ============================================================

class QuizAnswerSerializer(serializers.ModelSerializer):
    """Serializer cho Quiz Answer"""
    class Meta:
        model = QuizAnswer
        fields = [
            'id', 'question', 'selected_option',
            'text_answer', 'points_awarded'
        ]


class QuizSubmissionSerializer(serializers.ModelSerializer):
    """Serializer cho Quiz Submission"""
    user = UserListSerializer(read_only=True)
    quiz = QuizListSerializer(read_only=True)
    answers = QuizAnswerSerializer(many=True, read_only=True)
    lesson_id = serializers.IntegerField(source='lesson.id', read_only=True, allow_null=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, allow_null=True)
    
    class Meta:
        model = QuizSubmission
        fields = [
            'id', 'quiz', 'user', 'lesson', 'lesson_id', 'lesson_title',
            'total_score', 'status', 'started_at', 'submitted_at', 
            'quiz_snapshot', 'answers'
        ]


class QuizSubmissionCreateSerializer(serializers.Serializer):
    """Serializer để tạo Submission (bắt đầu làm bài)"""
    quiz_id = serializers.IntegerField()
    lesson_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_quiz_id(self, value):
        try:
            quiz = Quiz.objects.get(id=value)
            if not quiz.is_published:
                raise serializers.ValidationError("Quiz is not published")
        except Quiz.DoesNotExist:
            raise serializers.ValidationError("Quiz not found")
        return value
    
    def validate_lesson_id(self, value):
        if value is not None:
            from course.models import Lesson
            try:
                Lesson.objects.get(id=value)
            except Lesson.DoesNotExist:
                raise serializers.ValidationError("Lesson not found")
        return value


class QuizAnswerSubmitSerializer(serializers.Serializer):
    """Serializer để submit câu trả lời"""
    question_id = serializers.IntegerField()
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    text_answer = serializers.CharField(required=False, allow_blank=True)
