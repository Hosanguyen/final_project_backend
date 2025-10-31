from rest_framework import serializers
from .models import Problem, TestCase, TagProblem, Submissions
from course.models import Tag, Language
from users.serializers import UserListSerializer


# ============================================================
# TAG SERIALIZERS
# ============================================================

class TagSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


# ============================================================
# LANGUAGE SERIALIZERS
# ============================================================

class LanguageSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "code", "name"]


# ============================================================
# TEST CASE SERIALIZERS
# ============================================================

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "id", "type", "sequence", "input_data", "output_data",
            "time_limit_ms", "memory_limit_kb", "points",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TestCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "type", "sequence", "input_data", "output_data",
            "time_limit_ms", "memory_limit_kb", "points"
        ]


class TestCaseListSerializer(serializers.ModelSerializer):
    """Simplified test case for list view (hide data for secret tests)"""
    
    class Meta:
        model = TestCase
        fields = ["id", "type", "sequence", "points"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Chỉ hiển thị input/output cho sample tests
        if instance.type == "sample":
            data["input_data"] = instance.input_data
            data["output_data"] = instance.output_data
        return data


# ============================================================
# PROBLEM SERIALIZERS
# ============================================================

class ProblemListSerializer(serializers.ModelSerializer):
    """List view - Compact info"""
    tags = TagSimpleSerializer(many=True, read_only=True)
    test_case_count = serializers.SerializerMethodField()
    # submission_count = serializers.SerializerMethodField()
    # acceptance_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Problem
        fields = [
            "id", "slug", "title", "short_statement", "difficulty",
            "tags", "is_public", "is_synced_to_domjudge",
            "test_case_count", 
            # "submission_count", 
            # "acceptance_rate",
            "created_at"
        ]
    
    def get_test_case_count(self, obj):
        return obj.test_cases.count()
    
    # def get_submission_count(self, obj):
    #     return obj.submissions.count()
    
    # def get_acceptance_rate(self, obj):
    #     total = obj.submissions.count()
    #     if total == 0:
    #         return 0
    #     accepted = obj.submissions.filter(status="accepted").count()
    #     return round((accepted / total) * 100, 2)


class ProblemDetailSerializer(serializers.ModelSerializer):
    """Detail view - Full info"""
    tags = TagSimpleSerializer(many=True, read_only=True)
    allowed_languages = LanguageSimpleSerializer(many=True, read_only=True)
    test_cases = TestCaseSerializer(many=True, read_only=True)
    created_by = UserListSerializer(read_only=True)
    updated_by = UserListSerializer(read_only=True)
    
    test_case_count = serializers.SerializerMethodField()
    # submission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Problem
        fields = [
            "id", "slug", "title", "short_statement", "statement_text",
            "input_format", "output_format", "difficulty",
            "time_limit_ms", "memory_limit_kb", "source", "is_public",
            "editorial_text", "editorial_file",
            "domjudge_problem_id", "is_synced_to_domjudge", "last_synced_at",
            "tags", "allowed_languages", "test_cases",
            "test_case_count", 
            # "submission_count",
            "created_by", "created_at", "updated_by", "updated_at"
        ]
    
    def get_test_case_count(self, obj):
        return obj.test_cases.count()
    
    # def get_submission_count(self, obj):
    #     return obj.submissions.count()


class ProblemCreateSerializer(serializers.ModelSerializer):
    """Create problem with test cases"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    language_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    test_cases = TestCaseCreateSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Problem
        fields = [
            "slug", "title", "short_statement", "statement_text",
            "input_format", "output_format", "difficulty",
            "time_limit_ms", "memory_limit_kb", "source", "is_public",
            "editorial_text", "editorial_file",
            "tag_ids", "language_ids", "test_cases"
        ]
    
    def validate_slug(self, value):
        if Problem.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Slug đã tồn tại")
        return value
    
    def validate_tag_ids(self, value):
        if value:
            existing_count = Tag.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("Một số tag ID không tồn tại")
        return value
    
    def validate_language_ids(self, value):
        if value:
            existing_count = Language.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("Một số language ID không tồn tại")
        return value
    
    def create(self, validated_data):
        tag_ids = validated_data.pop("tag_ids", [])
        language_ids = validated_data.pop("language_ids", [])
        test_cases_data = validated_data.pop("test_cases", [])
        
        # Create problem
        problem = Problem.objects.create(**validated_data)
        
        # Set tags
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            problem.tags.set(tags)
        
        # Set languages
        if language_ids:
            languages = Language.objects.filter(id__in=language_ids)
            problem.allowed_languages.set(languages)
        
        # Create test cases
        for tc_data in test_cases_data:
            TestCase.objects.create(problem=problem, **tc_data)
        
        return problem


class ProblemUpdateSerializer(serializers.ModelSerializer):
    """Update problem (without test cases - use separate endpoint)"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    language_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Problem
        fields = [
            "title", "short_statement", "statement_text",
            "input_format", "output_format", "difficulty",
            "time_limit_ms", "memory_limit_kb", "source", "is_public",
            "editorial_text", "editorial_file",
            "tag_ids", "language_ids"
        ]
    
    def validate_tag_ids(self, value):
        if value is not None:
            existing_count = Tag.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("Một số tag ID không tồn tại")
        return value
    
    def validate_language_ids(self, value):
        if value is not None:
            existing_count = Language.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("Một số language ID không tồn tại")
        return value
    
    def update(self, instance, validated_data):
        tag_ids = validated_data.pop("tag_ids", None)
        language_ids = validated_data.pop("language_ids", None)
        
        # Update problem fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        
        # Update languages
        if language_ids is not None:
            languages = Language.objects.filter(id__in=language_ids)
            instance.allowed_languages.set(languages)
        
        return instance


# ============================================================
# SYNC TO DOMJUDGE SERIALIZER
# ============================================================

class SyncToDOMjudgeSerializer(serializers.Serializer):
    """Trigger sync to DOMjudge"""
    force = serializers.BooleanField(
        default=False,
        help_text="Force sync even if already synced"
    )


# ============================================================
# SUBMISSION SERIALIZERS
# ============================================================

class SubmissionCreateSerializer(serializers.Serializer):
    """Create submission"""
    language_id = serializers.IntegerField(required=True)
    code = serializers.CharField(required=True, allow_blank=False)
    
    def validate_language_id(self, value):
        if not Language.objects.filter(id=value).exists():
            raise serializers.ValidationError("Language không tồn tại")
        return value


class SubmissionSerializer(serializers.ModelSerializer):
    """Submission detail"""
    problem = ProblemListSerializer(read_only=True)
    user = UserListSerializer(read_only=True)
    language = LanguageSimpleSerializer(read_only=True)
    
    class Meta:
        model = Submissions
        fields = [
            "id", "problem", "user", "language",
            "code_text", "submitted_at", "status",
            "score", "feedback", "domjudge_submission_id"
        ]
        read_only_fields = ["id", "submitted_at"]


class SubmissionListSerializer(serializers.ModelSerializer):
    """Submission list (simplified)"""
    language = LanguageSimpleSerializer(read_only=True)
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = Submissions
        fields = [
            "id", "user", "language", "submitted_at",
            "status", "score"
        ]


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """Submission detail with judging results"""
    problem = ProblemListSerializer(read_only=True)
    user = UserListSerializer(read_only=True)
    language = LanguageSimpleSerializer(read_only=True)
    detailed_results = serializers.SerializerMethodField()
    
    class Meta:
        model = Submissions
        fields = [
            "id", "problem", "user", "language",
            "code_text", "submitted_at", "status",
            "score", "feedback", "domjudge_submission_id",
            "detailed_results"
        ]
        read_only_fields = ["id", "submitted_at"]
    
    def get_detailed_results(self, obj):
        """Get detailed judging results from DOMjudge database"""
        if not obj.domjudge_submission_id:
            return None
        
        from .domjudge_service import DOMjudgeService
        service = DOMjudgeService()
        
        try:
            results = service.get_detailed_judging_results(obj.domjudge_submission_id)
            return results
        except Exception as e:
            return {
                'verdict': 'error',
                'message': str(e)
            }