from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage

from .models import Contest, ContestProblem, ContestParticipant
from .serializers import (
    ContestCreateSerializer,
    ContestSerializer,
    ContestListSerializer,
    LeaderboardEntrySerializer
)
from .domjudge_service import DOMjudgeContestService
from .ranking_service import ContestRankingService
from problems.models import Submissions
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
            contest_mode_changed = False
            if 'contest_mode' in request.data and request.data['contest_mode'] != contest.contest_mode:
                contest_mode_changed = True
            serializer = ContestCreateSerializer(contest, data=request.data, partial=True, context={'request': request})
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            contest = serializer.save(updated_by=request.user)
            if contest_mode_changed:
                # Update lazy_eval_results in DOMjudge if contest_mode changed
                domjudge_service = DOMjudgeContestService()
                domjudge_service.update_lazy_eval_results_for_contest(contest)
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
                # DOMjudge: lazy_eval_results special handling
                # If contest is OI mode, force value 2
                if contest.contest_mode == 'OI':
                    lazy_eval_flag = 2
                else:
                    lazy_eval_flag = 1 if serializer.validated_data.get('lazy_eval_results', False) else 0

                domjudge_problem_data = {
                    'label': serializer.validated_data.get('label', ''),
                    'points': serializer.validated_data.get('points', 1),
                    'lazy_eval_results': lazy_eval_flag
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
            user = request.user
            
            # Calculate contest status
            now = timezone.now()
            if now < contest.start_at:
                contest_status = 'upcoming'
            elif now > contest.end_at:
                contest_status = 'finished'
            else:
                contest_status = 'running'
            
            # Check if user is registered for the contest
            is_registered = False
            registered_at = None
            try:
                participant = ContestParticipant.objects.get(
                    contest=contest,
                    user=user,
                    is_active=True
                )
                is_registered = True
                registered_at = participant.registered_at
            except ContestParticipant.DoesNotExist:
                pass
            
            # Show problems logic:
            # - If contest finished: everyone can view (registered or not)
            # - If contest running: only registered users can view
            # - If contest upcoming: no one can view
            problems_data = []
            can_view_problems = False
            
            if contest_status == 'finished' or (is_registered and contest_status == 'running'):
                can_view_problems = True
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
                'contest_mode': contest.contest_mode,
                'status': contest_status,
                'problem_count': ContestProblem.objects.filter(contest=contest).count(),
                'is_registered': is_registered,
                'registered_at': registered_at,
                'can_view_problems': can_view_problems,
                'problems': problems_data
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to fetch ContestProblem details',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestParticipantsView(APIView):
    """Get list of participants for a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        """Get all participants for a contest"""
        try:
            contest = Contest.objects.get(id=contest_id)
            
            # Get all participants (active and inactive)
            participants = ContestParticipant.objects.filter(
                contest=contest
            ).select_related('user').order_by('-registered_at')
            
            # Serialize participants
            from .serializers import ContestParticipantSerializer
            serializer = ContestParticipantSerializer(participants, many=True)
            
            # Count statistics
            total_count = participants.count()
            active_count = participants.filter(is_active=True).count()
            inactive_count = participants.filter(is_active=False).count()
            
            return Response({
                'participants': serializer.data,
                'statistics': {
                    'total': total_count,
                    'active': active_count,
                    'inactive': inactive_count
                }
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Cuộc thi không tồn tại'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể tải danh sách người tham gia',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestParticipantToggleView(APIView):
    """Toggle participant active status"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, contest_id, participant_id):
        """Deactivate active participant (Admin only can deactivate, not reactivate)"""
        try:
            contest = Contest.objects.get(id=contest_id)
            participant = ContestParticipant.objects.get(
                id=participant_id,
                contest=contest
            )
            
            # Only allow deactivating active participants
            if not participant.is_active:
                return Response({
                    'error': 'Không thể kích hoạt lại người tham gia đã hủy đăng ký'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Deactivate participant
            participant.is_active = False
            participant.save()
            
            # Serialize updated participant
            from .serializers import ContestParticipantSerializer
            serializer = ContestParticipantSerializer(participant)
            
            return Response({
                'message': 'Hủy kích hoạt người tham gia thành công',
                'participant': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Cuộc thi không tồn tại'
            }, status=status.HTTP_404_NOT_FOUND)
        except ContestParticipant.DoesNotExist:
            return Response({
                'error': 'Không tìm thấy người tham gia'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể hủy kích hoạt người tham gia',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestUserCandidatesView(APIView):
    """List user candidates for adding to contest (searchable)"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, contest_id):
        from users.models import User
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({'error': 'Cuộc thi không tồn tại'}, status=status.HTTP_404_NOT_FOUND)

        q = request.query_params.get('q', '').strip()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        exclude_participating = request.query_params.get('exclude_participating', 'true').lower() != 'false'

        # Validate pagination params
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        queryset = User.objects.all()

        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(full_name__icontains=q)
            )

        if exclude_participating:
            # Exclude only users currently active in this contest; allow previously inactive participants to appear
            participant_user_ids = ContestParticipant.objects.filter(
                contest=contest,
                is_active=True
            ).values_list('user_id', flat=True)
            queryset = queryset.exclude(id__in=participant_user_ids)

        queryset = queryset.order_by('username')

        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page = paginator.num_pages if paginator.num_pages > 0 else 1
            page_obj = paginator.page(page)

        def avatar(u):
            try:
                return u.avatar_url.url if u.avatar_url and hasattr(u.avatar_url, 'url') else None
            except Exception:
                return None

        data = [
            {
                'id': u.id,
                'username': u.username,
                'full_name': getattr(u, 'full_name', '') or u.username,
                'email': u.email,
                'avatar_url': avatar(u)
            }
            for u in page_obj.object_list
        ]

        return Response({
            'results': data,
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        }, status=status.HTTP_200_OK)


class ContestParticipantsBulkAddView(APIView):
    """Bulk add users as participants to a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, contest_id):
        from users.models import User
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return Response({'error': 'Cuộc thi không tồn tại'}, status=status.HTTP_404_NOT_FOUND)

        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return Response({'error': 'Danh sách user_ids không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(id__in=user_ids)
        found_ids = set(users.values_list('id', flat=True))

        added = []
        existed = []
        for uid in found_ids:
            participant, created = ContestParticipant.objects.get_or_create(
                contest=contest,
                user_id=uid,
                defaults={'is_active': True}
            )
            if not created:
                if not participant.is_active:
                    participant.is_active = True
                    participant.save(update_fields=['is_active'])
                existed.append(uid)
            else:
                added.append(uid)

        missing = [uid for uid in user_ids if uid not in found_ids]

        return Response({
            'message': 'Đã xử lý thêm người tham gia',
            'added_count': len(added),
            'existed_count': len(existed),
            'missing_count': len(missing),
            'added_user_ids': added,
            'existed_user_ids': existed,
            'missing_user_ids': missing
        }, status=status.HTTP_200_OK)


class ContestRegistrationView(APIView):
    """Register or unregister from a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, contest_id):
        """Register for a contest"""
        try:
            contest = Contest.objects.get(id=contest_id, visibility='public')
            user = request.user
            
            # Check if contest has ended
            now = timezone.now()
            if now > contest.end_at:
                return Response({
                    'error': 'Không thể đăng ký cuộc thi đã kết thúc'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user is already registered
            participant, created = ContestParticipant.objects.get_or_create(
                contest=contest,
                user=user,
                defaults={'is_active': True}
            )
            
            if not created:
                # If already exists, reactivate if previously cancelled
                if not participant.is_active:
                    participant.is_active = True
                    participant.save()
                    return Response({
                        'message': 'Đăng ký lại cuộc thi thành công',
                        'registered_at': participant.registered_at
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Đã đăng ký cuộc thi này',
                        'registered_at': participant.registered_at
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'message': 'Đăng ký cuộc thi thành công',
                'registered_at': participant.registered_at
            }, status=status.HTTP_201_CREATED)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Cuộc thi không tồn tại'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể đăng ký cuộc thi',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, contest_id):
        """Unregister from a contest"""
        try:
            contest = Contest.objects.get(id=contest_id, visibility='public')
            user = request.user
            
            # Check if contest has started or registration period ended
            now = timezone.now()
            if now >= contest.start_at:
                return Response({
                    'error': 'Không thể hủy đăng ký sau khi cuộc thi đã bắt đầu'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find participant record
            try:
                participant = ContestParticipant.objects.get(
                    contest=contest,
                    user=user
                )
                
                # Deactivate instead of delete to keep history
                participant.is_active = False
                participant.save()
                
                return Response({
                    'message': 'Hủy đăng ký cuộc thi thành công'
                }, status=status.HTTP_200_OK)
                
            except ContestParticipant.DoesNotExist:
                return Response({
                    'error': 'Chưa đăng ký cuộc thi này'
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Cuộc thi không tồn tại'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể hủy đăng ký cuộc thi',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestRegistrationStatusView(APIView):
    """Check if user is registered for a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        """Get registration status for current user"""
        try:
            contest = Contest.objects.get(id=contest_id, visibility='public')
            user = request.user
            
            try:
                participant = ContestParticipant.objects.get(
                    contest=contest,
                    user=user
                )
                
                return Response({
                    'is_registered': participant.is_active,
                    'registered_at': participant.registered_at if participant.is_active else None
                }, status=status.HTTP_200_OK)
                
            except ContestParticipant.DoesNotExist:
                return Response({
                    'is_registered': False,
                    'registered_at': None
                }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Cuộc thi không tồn tại'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể kiểm tra trạng thái đăng ký',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestProblemDetailView(APIView):
    """Get ContestProblem details by id"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_problem_id):
        try:
            contest_problem = ContestProblem.objects.select_related(
                'contest', 'problem'
            ).get(id=contest_problem_id)
            
            from .serializers import ContestProblemDetailSerializer
            serializer = ContestProblemDetailSerializer(contest_problem)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Không tìm thấy ContestProblem'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Không thể tải chi tiết ContestProblem',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestLeaderboardView(APIView):
    """Get leaderboard for a contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        """Get contest leaderboard with rankings"""
        try:
            contest = Contest.objects.get(id=contest_id)
            
            # Get contest problems for column headers
            contest_problems = ContestProblem.objects.filter(
                contest=contest
            ).select_related('problem').order_by('label')
            
            problem_list = [{
                'id': cp.problem.id,
                'label': cp.label,
                'alias': cp.alias,
                'point': cp.point,
                'title': cp.problem.title
            } for cp in contest_problems]
            
            # Get rankings
            participants = ContestRankingService.get_contest_leaderboard(contest_id)
            
            # Build leaderboard entries
            leaderboard_data = []
            current_rank = 1
            
            for idx, participant in enumerate(participants, start=1):
                # Get problem details for this user (for ICPC mode)
                problem_details = {}
                if contest.contest_mode == 'ICPC' or contest.slug == 'practice':
                    problem_details = ContestRankingService.get_user_problem_details(
                        contest_id,
                        participant.user.id
                    )
                
                # Get full name
                full_name = participant.user.full_name if participant.user.full_name else participant.user.username
                
                # Get avatar URL properly
                avatar_url = None
                if participant.user.avatar_url:
                    avatar_url = participant.user.avatar_url.url if hasattr(participant.user.avatar_url, 'url') else str(participant.user.avatar_url)
                
                # Attempted problems (distinct problems with any submission)
                attempted_count = None
                try:
                    # Only compute for practice to avoid heavy queries elsewhere
                    if contest.slug == 'practice':
                        # Count distinct problems the user has ever submitted within the window
                        attempted_count = Submissions.objects.filter(
                            contest=contest,
                            user=participant.user,
                            submitted_at__gte=contest.start_at,
                            submitted_at__lte=contest.end_at
                        ).values('problem').distinct().count()
                except Exception:
                    attempted_count = None

                entry = {
                    'rank': current_rank,
                    'user_id': participant.user.id,
                    'username': participant.user.username,
                    'full_name': full_name,
                    'avatar_url': avatar_url,
                    'solved_count': participant.solved_count,
                    'total_score': float(participant.total_score),
                    'penalty_seconds': participant.penalty_seconds,
                    'penalty_minutes': participant.penalty_seconds // 60,
                    'last_submission_at': participant.last_submission_at,
                    'problems': problem_details,
                    'attempted_count': attempted_count
                }
                
                leaderboard_data.append(entry)
                current_rank += 1
            
            return Response({
                'contest_id': contest.id,
                'contest_slug': contest.slug,
                'contest_title': contest.title,
                'contest_mode': contest.contest_mode,
                'penalty_time': contest.penalty_time,
                'problems': problem_list,
                'leaderboard': leaderboard_data,
                'total_participants': len(leaderboard_data)
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to fetch leaderboard',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContestRecalculateRankingsView(APIView):
    """Trigger a full rankings recalculation for a contest (admin utility)"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, contest_id):
        try:
            # Ensure contest exists
            try:
                contest = Contest.objects.get(id=contest_id)
            except Contest.DoesNotExist:
                return Response({'error': 'Contest not found'}, status=status.HTTP_404_NOT_FOUND)

            # Recalculate rankings for all active participants
            updated_count = ContestRankingService.recalculate_all_rankings(contest_id)

            return Response({
                'message': 'Đã tính lại xếp hạng',
                'updated_participants': updated_count,
                'contest_id': contest.id,
                'contest_slug': contest.slug
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Không thể tính lại xếp hạng',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)