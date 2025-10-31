from rest_framework import serializers
from .models import Contest, ContestProblem
from problems.models import Problem
from users.models import User


class ContestProblemSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(write_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    problem_slug = serializers.CharField(source='problem.slug', read_only=True)
    
    class Meta:
        model = ContestProblem
        fields = ['id', 'problem_id', 'problem_title', 'problem_slug', 'sequence', 'alias']
        

class ContestCreateSerializer(serializers.ModelSerializer):
    problems = ContestProblemSerializer(many=True, required=False, write_only=True)
    
    class Meta:
        model = Contest
        fields = [
            'slug', 'title', 'description', 'start_at', 'end_at',
            'visibility', 'penalty_time', 'penalty_mode', 
            'freeze_rankings_at', 'problems'
        ]
    
    def validate_slug(self, value):
        """Validate that slug is unique and follows naming convention"""
        if Contest.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Contest with this slug already exists.")
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Slug can only contain alphanumeric characters, hyphens, and underscores.")
        return value
    
    def validate(self, data):
        """Validate start_at and end_at"""
        if data['end_at'] <= data['start_at']:
            raise serializers.ValidationError("End time must be after start time.")
        return data
    
    def create(self, validated_data):
        problems_data = validated_data.pop('problems', [])
        user = self.context['request'].user
        
        contest = Contest.objects.create(
            **validated_data,
            created_by=user,
            updated_by=user
        )
        
        # Create contest problems
        for problem_data in problems_data:
            problem_id = problem_data.pop('problem_id')
            try:
                problem = Problem.objects.get(id=problem_id)
                ContestProblem.objects.create(
                    contest=contest,
                    problem=problem,
                    **problem_data
                )
            except Problem.DoesNotExist:
                pass  # Skip if problem doesn't exist
        
        return contest


class ContestSerializer(serializers.ModelSerializer):
    problems = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    problem_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'description', 'start_at', 'end_at',
            'visibility', 'penalty_time', 'penalty_mode', 'freeze_rankings_at',
            'created_at', 'updated_at', 'created_by_name', 'updated_by_name',
            'problems', 'problem_count'
        ]
    
    def get_problems(self, obj):
        contest_problems = obj.contest_problems.all()
        return ContestProblemSerializer(contest_problems, many=True).data
    
    def get_problem_count(self, obj):
        return obj.contest_problems.count()


class ContestListSerializer(serializers.ModelSerializer):
    problem_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'start_at', 'end_at',
            'visibility', 'penalty_time', 'problem_count',
            'created_by_name', 'status', 'created_at'
        ]
    
    def get_problem_count(self, obj):
        return obj.contest_problems.count()
    
    def get_status(self, obj):
        from django.utils import timezone
        now = timezone.now()
        
        if now < obj.start_at:
            return 'upcoming'
        elif now > obj.end_at:
            return 'finished'
        else:
            return 'running'
