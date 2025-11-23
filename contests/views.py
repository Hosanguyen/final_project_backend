from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from .models import Contest, ContestProblem
from .serializers import (
    ContestCreateSerializer,
    ContestSerializer,
    ContestListSerializer
)
from .domjudge_service import DOMjudgeContestService
from common.authentication import CustomJWTAuthentication


class ContestCreateView(APIView):
    """Create a new contest and sync with DOMjudge"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ContestCreateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create contest in database
            contest = serializer.save()
            
            # Prepare data for DOMjudge
            duration = contest.end_at - contest.start_at
            duration_str = self._format_duration(duration)
            
            # Calculate freeze duration if freeze_rankings_at is set
            freeze_duration_str = None
            if contest.freeze_rankings_at:
                freeze_duration = contest.end_at - contest.freeze_rankings_at
                freeze_duration_str = self._format_duration(freeze_duration)
            
            domjudge_data = {
                'id': contest.slug,
                'name': contest.title,
                'formal_name': contest.title,
                'start_time': contest.start_at.isoformat(),
                'duration': duration_str,
                'penalty_time': contest.penalty_time
            }
            
            if freeze_duration_str:
                domjudge_data['scoreboard_freeze_duration'] = freeze_duration_str
            
            # Create contest in DOMjudge
            domjudge_service = DOMjudgeContestService()
            domjudge_contest_id = domjudge_service.create_contest(domjudge_data)
            
            # Return response
            response_serializer = ContestSerializer(contest)
            return Response({
                'message': 'Contest created successfully',
                'contest': response_serializer.data,
                'domjudge_contest_id': domjudge_contest_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # If DOMjudge creation fails, delete the contest from database
            if 'contest' in locals():
                contest.delete()
            
            return Response({
                'error': 'Failed to create contest',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _format_duration(self, duration):
        """Format timedelta to HH:MM:SS string"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"


class ContestListView(APIView):
    """List all contests"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        contests = Contest.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            now = timezone.now()
            if status_filter == 'upcoming':
                contests = contests.filter(start_at__gt=now)
            elif status_filter == 'running':
                contests = contests.filter(start_at__lte=now, end_at__gte=now)
            elif status_filter == 'finished':
                contests = contests.filter(end_at__lt=now)
        
        # Filter by visibility
        visibility_filter = request.query_params.get('visibility', None)
        if visibility_filter:
            contests = contests.filter(visibility=visibility_filter)
        
        serializer = ContestListSerializer(contests, many=True)
        return Response({
            'contests': serializer.data,
            'total': contests.count()
        }, status=status.HTTP_200_OK)


class ContestDetailView(APIView):
    """Get, update, or delete a specific contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            serializer = ContestSerializer(contest)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            serializer = ContestCreateSerializer(contest, data=request.data, partial=True, context={'request': request})
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            contest = serializer.save(updated_by=request.user)
            response_serializer = ContestSerializer(contest)
            
            return Response({
                'message': 'Contest updated successfully',
                'contest': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            
            # Try to delete from DOMjudge
            try:
                domjudge_service = DOMjudgeContestService()
                domjudge_service.delete_contest(contest.slug)
            except Exception as e:
                # Log error but continue with local deletion
                print(f"Failed to delete from DOMjudge: {str(e)}")
            
            contest.delete()
            
            return Response({
                'message': 'Contest deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ContestProblemView(APIView):
    """Add or remove problems from a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, contest_id):
        """Add a problem to the contest"""
        from .serializers import AddProblemToContestSerializer
        from problems.models import Problem
        
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddProblemToContestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem_id = serializer.validated_data['problem_id']
            problem = Problem.objects.get(id=problem_id)
            
            # Check if problem is already in contest
            if ContestProblem.objects.filter(contest=contest, problem=problem).exists():
                return Response({
                    'error': 'Problem is already in this contest'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get sequence number (auto-increment)
            max_sequence = ContestProblem.objects.filter(contest=contest).count()
            sequence = serializer.validated_data.get('sequence', max_sequence)
            
            # Create contest problem in database
            contest_problem = ContestProblem.objects.create(
                contest=contest,
                problem=problem,
                sequence=sequence,
                alias=serializer.validated_data.get('label', ''),
                label=serializer.validated_data.get('label', ''),
                color=serializer.validated_data.get('color', ''),
                rgb=serializer.validated_data.get('rgb', ''),
                point=serializer.validated_data.get('points', 1),
                lazy_eval_results=serializer.validated_data.get('lazy_eval_results', False)
            )
            
            # Sync with DOMjudge
            try:
                domjudge_service = DOMjudgeContestService()
                domjudge_problem_data = {
                    'label': serializer.validated_data.get('label', ''),
                    'points': serializer.validated_data.get('points', 1),
                    'lazy_eval_results': 1 if serializer.validated_data.get('lazy_eval_results', False) else 0
                }
                
                # Add optional fields
                if serializer.validated_data.get('color'):
                    domjudge_problem_data['color'] = serializer.validated_data['color']
                if serializer.validated_data.get('rgb'):
                    domjudge_problem_data['rgb'] = serializer.validated_data['rgb']
                
                domjudge_response = domjudge_service.add_problem_to_contest(
                    contest.slug,
                    problem.slug,
                    domjudge_problem_data
                )
                
                return Response({
                    'message': 'Problem added to contest successfully',
                    'contest_problem': {
                        'id': contest_problem.id,
                        'problem_id': problem.id,
                        'problem_title': problem.title,
                        'problem_slug': problem.slug,
                        'sequence': contest_problem.sequence,
                        'alias': contest_problem.alias,
                        'label': contest_problem.label,
                        'color': contest_problem.color,
                        'rgb': contest_problem.rgb,
                        'point': contest_problem.point
                    },
                    'domjudge_response': domjudge_response
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                # Rollback database changes if DOMjudge sync fails
                contest_problem.delete()
                return Response({
                    'error': 'Failed to sync with DOMjudge',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to add problem to contest',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, contest_id, problem_id):
        """Remove a problem from the contest"""
        from problems.models import Problem
        
        try:
            contest = Contest.objects.get(id=contest_id)
            problem = Problem.objects.get(id=problem_id)
            
            # Find contest problem
            try:
                contest_problem = ContestProblem.objects.get(contest=contest, problem=problem)
            except ContestProblem.DoesNotExist:
                return Response({
                    'error': 'Problem is not in this contest'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Remove from DOMjudge first
            try:
                domjudge_service = DOMjudgeContestService()
                domjudge_service.remove_problem_from_contest(contest.slug, problem.slug)
            except Exception as e:
                return Response({
                    'error': 'Failed to remove problem from DOMjudge',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Remove from database
            contest_problem.delete()
            
            return Response({
                'message': 'Problem removed from contest successfully'
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to remove problem from contest',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContestDetailUserView(APIView):
    """Get, update, or delete a specific contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            contest = Contest.objects.get(slug='practice')
            
            # Get pagination parameters
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Validate pagination parameters
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            # Get all contest problems
            contest_problems = ContestProblem.objects.filter(contest=contest).order_by('sequence')
            total_count = contest_problems.count()
            
            # Calculate pagination
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            # Get paginated problems
            paginated_problems = contest_problems[start_index:end_index]
            
            # Serialize problems
            from .serializers import ContestProblemSerializer
            problems_serializer = ContestProblemSerializer(
                paginated_problems, 
                many=True, 
                context={'request': request}
            )
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            
            return Response({
                'id': contest.id,
                'slug': contest.slug,
                'title': contest.title,
                'description': contest.description,
                'start_at': contest.start_at,
                'end_at': contest.end_at,
                'visibility': contest.visibility,
                'problems': problems_serializer.data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_items': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1
                }
            }, status=status.HTTP_200_OK)
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)


class UserContestsView(APIView):
    """Get all contests excluding practice contest for user header"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get all contests excluding practice
            contests = Contest.objects.exclude(slug='practice').filter(visibility='public')
            
            now = timezone.now()
            
            # Categorize contests
            upcoming = []
            running = []
            finished = []
            
            for contest in contests:
                contest_data = {
                    'id': contest.id,
                    'slug': contest.slug,
                    'title': contest.title,
                    'start_at': contest.start_at,
                    'end_at': contest.end_at,
                }
                
                if contest.start_at > now:
                    upcoming.append(contest_data)
                elif contest.start_at <= now and contest.end_at >= now:
                    running.append(contest_data)
                else:
                    finished.append(contest_data)
            
            # Sort each category
            upcoming.sort(key=lambda x: x['start_at'])
            running.sort(key=lambda x: x['start_at'])
            finished.sort(key=lambda x: x['end_at'], reverse=True)
            
            # Limit finished contests to most recent 5
            finished = finished[:5]
            
            return Response({
                'upcoming': upcoming,
                'running': running,
                'finished': finished
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch contests',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserContestDetailView(APIView):
    """Get contest details for user with problems sorted by label"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id, visibility='public')
            
            # Calculate contest status
            now = timezone.now()
            if now < contest.start_at:
                contest_status = 'upcoming'
            elif now > contest.end_at:
                contest_status = 'finished'
            else:
                contest_status = 'running'
            
            # Only show problems if contest has started
            problems_data = []
            if contest_status != 'upcoming':
                # Get contest problems sorted by label
                contest_problems = ContestProblem.objects.filter(
                    contest=contest
                ).select_related('problem').order_by('label')
                
                # Serialize problems with user status
                from .serializers import ContestProblemSerializer
                problems_serializer = ContestProblemSerializer(
                    contest_problems,
                    many=True,
                    context={'request': request}
                )
                problems_data = problems_serializer.data
            
            return Response({
                'id': contest.id,
                'slug': contest.slug,
                'title': contest.title,
                'description': contest.description,
                'start_at': contest.start_at,
                'end_at': contest.end_at,
                'penalty_time': contest.penalty_time,
                'penalty_mode': contest.penalty_mode,
                'status': contest_status,
                'problem_count': ContestProblem.objects.filter(contest=contest).count(),
                'problems': problems_data
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to fetch contest details',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)