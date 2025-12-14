from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .models import User
from common.authentication import CustomJWTAuthentication


class PublicUserProfileView(APIView):
    """
    API để xem thông tin public của user khác
    Không cần authentication, chỉ trả về thông tin công khai
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Lấy thống kê submissions
            from problems.models import Submissions
            total_submissions = Submissions.objects.filter(user=user).count()
            accepted_submissions = Submissions.objects.filter(
                user=user, 
                status__in=['ac', 'correct', 'accepted']
            ).count()
            
            # Lấy unique problems đã solve (AC)
            from problems.user_profile_views import normalize_status
            user_submissions = Submissions.objects.filter(user=user).select_related('problem')
            solved_problems = set()
            for sub in user_submissions:
                if normalize_status(sub.status) == 'accepted':
                    solved_problems.add(sub.problem.id)
            
            # Lấy danh sách contests đã tham gia
            from contests.models import ContestParticipant
            participated_contests = ContestParticipant.objects.filter(
                user=user
            ).count()
            
            # Build avatar URL
            avatar_url = None
            if user.avatar_url:
                try:
                    avatar_url = request.build_absolute_uri(user.avatar_url.url)
                except:
                    avatar_url = None
            
            # Build response data - chỉ thông tin public
            profile_data = {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name or '',
                'avatar_url': avatar_url,
                'bio': user.bio or '' if hasattr(user, 'bio') else '',
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                
                # Rating info từ User model
                'rating': {
                    'current_rating': getattr(user, 'current_rating', 1000),
                    'rank_title': getattr(user, 'rank', 'newbie'),
                    'global_rank': getattr(user, 'global_rank', None),
                    'max_rating': getattr(user, 'max_rating', 1000),
                    'contests_participated': getattr(user, 'contests_participated', 0),
                },
                
                # Statistics
                'statistics': {
                    'total_submissions': total_submissions,
                    'accepted_submissions': accepted_submissions,
                    'problems_solved': len(solved_problems),
                    'contests_participated': participated_contests,
                    'acceptance_rate': round((accepted_submissions / total_submissions * 100), 2) if total_submissions > 0 else 0,
                }
            }
            
            return Response(profile_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user profile',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicUserProblemsView(APIView):
    """
    API để xem danh sách problems mà user đã solve (chỉ AC)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            from problems.models import Submissions
            from problems.user_profile_views import normalize_status
            
            # Lấy tất cả submissions AC của user
            user_submissions = Submissions.objects.filter(
                user=user
            ).select_related('problem').order_by('-submitted_at')
            
            # Tính unique problems đã AC
            problems_map = {}
            for sub in user_submissions:
                if normalize_status(sub.status) == 'accepted':
                    problem_id = sub.problem.id
                    if problem_id not in problems_map:
                        problems_map[problem_id] = {
                            'problem_id': sub.problem.id,
                            'problem_title': sub.problem.title,
                            'problem_slug': sub.problem.slug,
                            'difficulty': sub.problem.difficulty,
                            'solved_at': sub.submitted_at.isoformat(),
                        }
            
            problems_list = list(problems_map.values())
            
            # Pagination
            total = len(problems_list)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_problems = problems_list[start_idx:end_idx]
            
            return Response({
                'problems': paginated_problems,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total > 0 else 0
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user problems',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicUserContestsView(APIView):
    """
    API để xem danh sách contests mà user đã tham gia
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            from contests.models import ContestParticipant
            
            # Lấy contests đã tham gia, loại bỏ contest practice
            participants = ContestParticipant.objects.filter(
                user=user
            ).exclude(
                contest__slug='practice'
            ).select_related('contest').order_by('-registered_at')
            
            total = participants.count()
            
            # Pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_participants = participants[start_idx:end_idx]
            
            contests_data = []
            for participant in paginated_participants:
                contest = participant.contest
                contests_data.append({
                    'id': contest.id,
                    'title': contest.title,
                    'start_at': contest.start_at.isoformat(),
                    'end_at': contest.end_at.isoformat(),
                    'participated_at': participant.registered_at.isoformat(),
                })
            
            return Response({
                'contests': contests_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total > 0 else 0
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user contests',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
