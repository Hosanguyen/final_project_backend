from rest_framework import serializers
from .models import Contest, ContestProblem
from problems.models import Problem
from users.models import User


class ContestProblemSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source='problem.id', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    problem_slug = serializers.CharField(source='problem.slug', read_only=True)
    problem_difficulty = serializers.CharField(source='problem.difficulty', read_only=True)
    user_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestProblem
        fields = ['id', 'problem_id', 'problem_title', 'problem_slug', 'problem_difficulty',
                  'sequence', 'alias', 'label', 'color', 'rgb', 'point', 'lazy_eval_results',
                  'user_status']
    
    def get_user_status(self, obj):
        """Get user's submission status for this problem"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            print(f"[DEBUG] Returning None - no authenticated user")
            return None
        
        from problems.models import Submissions
        
        try:
            # Get all submissions for this user and problem
            submissions = Submissions.objects.filter(
                user=request.user,
                problem=obj.problem
            ).order_by('-submitted_at')
            
            print(f"[DEBUG] Found {submissions.count()} submissions for user={request.user.id}, problem={obj.problem.id}")
            
            if not submissions.exists():
                return None
            
            # Find best status (AC > WA > others)
            has_ac = False
            has_wa = False
            total_count = submissions.count()
            
            for sub in submissions:
                status = (sub.status or '').lower()
                if status == 'ac' or status == 'correct':
                    has_ac = True
                    break
                elif status == 'wa' or status == 'wrong-answer':
                    has_wa = True
            
            result = None
            if has_ac:
                result = {'status': 'AC', 'count': total_count}
            elif has_wa:
                result = {'status': 'WA', 'count': total_count}
            else:
                result = {'status': 'ATTEMPTED', 'count': total_count}
            
            return result
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
        

class ContestCreateSerializer(serializers.ModelSerializer):
    problems = ContestProblemSerializer(many=True, required=False, write_only=True)
    
    class Meta:
        model = Contest
        fields = [
            'slug', 'title', 'description', 'start_at', 'end_at',
            'visibility', 'contest_mode', 'is_show_result', 'penalty_time', 'penalty_mode', 
            'freeze_rankings_at', 'problems'
        ]
    
    def validate_slug(self, value):
        """Validate that slug is unique and follows naming convention"""
        # Skip validation if updating (instance exists)
        if self.instance and self.instance.slug == value:
            return value
            
        if Contest.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Contest with this slug already exists.")
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError("Slug can only contain alphanumeric characters, hyphens, and underscores.")
        return value
    
    def validate(self, data):
        """Validate start_at and end_at"""
        # Get existing values if updating
        start_at = data.get('start_at', getattr(self.instance, 'start_at', None) if self.instance else None)
        end_at = data.get('end_at', getattr(self.instance, 'end_at', None) if self.instance else None)
        
        if start_at and end_at and end_at <= start_at:
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
    
    def update(self, instance, validated_data):
        """Update contest - ignore problems field in update"""
        # Remove problems from validated_data if present
        validated_data.pop('problems', None)
        
        # Update contest fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Set updated_by if available
        if 'request' in self.context:
            instance.updated_by = self.context['request'].user
        
        instance.save()
        return instance


class ContestSerializer(serializers.ModelSerializer):
    problems = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    problem_count = serializers.SerializerMethodField()
    is_show_result = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'description', 'start_at', 'end_at',
            'visibility', 'contest_mode', 'is_show_result', 'penalty_time', 'penalty_mode', 'freeze_rankings_at',
            'created_at', 'updated_at', 'created_by_name', 'updated_by_name',
            'problems', 'problem_count'
        ]
    
    def get_problems(self, obj):
        contest_problems = obj.contest_problems.all()
        # Pass request context to ContestProblemSerializer
        return ContestProblemSerializer(
            contest_problems, 
            many=True, 
            context=self.context
        ).data
    
    def get_problem_count(self, obj):
        return obj.contest_problems.count()
    
    def get_is_show_result(self, obj):
        """Automatically determine is_show_result based on contest status"""
        from django.utils import timezone
        now = timezone.now()
        
        # If contest has ended, show results
        if now > obj.end_at:
            return True
        # If contest is running or upcoming, hide results
        else:
            return False


class ContestListSerializer(serializers.ModelSerializer):
    problem_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    status = serializers.SerializerMethodField()
    is_show_result = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'slug', 'title', 'start_at', 'end_at',
            'visibility', 'contest_mode', 'is_show_result', 'penalty_time', 'problem_count',
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
    
    def get_is_show_result(self, obj):
        """Automatically determine is_show_result based on contest status"""
        from django.utils import timezone
        now = timezone.now()
        
        # If contest has ended, show results
        if now > obj.end_at:
            return True
        # If contest is running or upcoming, hide results
        else:
            return False


class AddProblemToContestSerializer(serializers.Serializer):
    """Serializer for adding a problem to a contest"""
    problem_id = serializers.IntegerField(required=True)
    label = serializers.CharField(required=True, max_length=10)
    color = serializers.CharField(required=False, allow_blank=True, max_length=50)
    rgb = serializers.CharField(required=False, allow_blank=True, max_length=7)
    points = serializers.IntegerField(required=False, default=1)
    lazy_eval_results = serializers.BooleanField(required=False, default=False)
    sequence = serializers.IntegerField(required=False)
    
    def validate_problem_id(self, value):
        """Validate that problem exists"""
        try:
            Problem.objects.get(id=value)
        except Problem.DoesNotExist:
            raise serializers.ValidationError("Problem does not exist.")
        return value


class ContestProblemDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ContestProblem including full contest and problem data"""
    contest = serializers.SerializerMethodField()
    problem = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestProblem
        fields = [
            'id', 'contest', 'problem', 'sequence', 'alias', 
            'label', 'color', 'rgb', 'point', 'lazy_eval_results'
        ]
    
    def get_contest(self, obj):
        """Return contest data"""
        from django.utils import timezone
        now = timezone.now()
        
        status = 'upcoming'
        if now < obj.contest.start_at:
            status = 'upcoming'
        elif now > obj.contest.end_at:
            status = 'finished'
        else:
            status = 'running'
        
        # Determine is_show_result based on contest status
        from django.utils import timezone
        now = timezone.now()
        is_show_result = True if now > obj.contest.end_at else False
        
        return {
            'id': obj.contest.id,
            'slug': obj.contest.slug,
            'title': obj.contest.title,
            'description': obj.contest.description,
            'start_at': obj.contest.start_at,
            'end_at': obj.contest.end_at,
            'visibility': obj.contest.visibility,
            'contest_mode': obj.contest.contest_mode,
            'is_show_result': is_show_result,
            'penalty_time': obj.contest.penalty_time,
            'penalty_mode': obj.contest.penalty_mode,
            'status': status
        }
    
    def get_problem(self, obj):
        """Return problem data"""
        from problems.serializers import ProblemDetailSerializer
        return ProblemDetailSerializer(obj.problem).data
