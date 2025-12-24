from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Submissions
from common.authentication import CustomJWTAuthentication


def normalize_status(status_code):
    """Chuẩn hóa status codes từ DOMjudge"""
    if not status_code:
        return 'pending'
    
    status_code = status_code.lower().strip()
    status_map = {
        'ac': 'accepted',
        'correct': 'accepted',
        'wa': 'wrong',
        'no': 'wrong',
        'tle': 'time_limit',
        'mle': 'memory_limit',
        'rte': 'runtime_error',
        'error': 'runtime_error',
        'ce': 'compile_error',
        'judging': 'judging',
        'pending': 'pending',
    }
    
    return status_map.get(status_code, status_code)


class UserProblemsView(APIView):
    """
    API mới cho UserProfile - Tab Problems
    Trả về danh sách unique problems mà user đã từng submit
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Lấy tất cả submissions của user
            user_submissions = Submissions.objects.filter(user=user).select_related(
                'problem', 'language', 'contest'
            ).order_by('-submitted_at')
            
            # Tính unique problems với thông tin tổng hợp
            problems_map = {}
            for sub in user_submissions:
                problem_id = sub.problem.id
                if problem_id not in problems_map:
                    # Tìm contest_problem_id nếu có
                    contest_problem_id = None
                    if sub.contest:
                        from contests.models import ContestProblem
                        contest_problem = ContestProblem.objects.filter(
                            contest=sub.contest,
                            problem=sub.problem
                        ).first()
                        if contest_problem:
                            contest_problem_id = contest_problem.id
                    
                    problems_map[problem_id] = {
                        'problem_id': sub.problem.id,
                        'problem_title': sub.problem.title,
                        'problem_slug': sub.problem.slug,
                        'difficulty': sub.problem.difficulty,
                        'submission_count': 1,
                        'last_submitted': sub.submitted_at.isoformat(),
                        'best_status': normalize_status(sub.status),
                        'has_accepted': normalize_status(sub.status) == 'accepted',
                        'contest_problem_id': contest_problem_id,
                    }
                else:
                    problems_map[problem_id]['submission_count'] += 1
                    # Update best_status: ưu tiên AC, nếu chưa có AC thì lấy status mới nhất
                    current_has_accepted = problems_map[problem_id].get('has_accepted', False)
                    normalized_status = normalize_status(sub.status)
                    is_accepted = normalized_status == 'accepted'
                    
                    if is_accepted and not current_has_accepted:
                        # Nếu tìm thấy AC và chưa có AC trước đó
                        problems_map[problem_id]['best_status'] = normalized_status
                        problems_map[problem_id]['has_accepted'] = True
                    elif not current_has_accepted:
                        # Nếu chưa có AC, lấy status không phải judging/pending
                        if normalized_status not in ['judging', 'pending']:
                            problems_map[problem_id]['best_status'] = normalized_status
                    
                    # Update last_submitted nếu mới hơn
                    current_last = problems_map[problem_id]['last_submitted']
                    if sub.submitted_at.isoformat() > current_last:
                        problems_map[problem_id]['last_submitted'] = sub.submitted_at.isoformat()
            
            # Convert to list và xóa field has_accepted trước khi trả về
            problems_list = []
            for prob in problems_map.values():
                prob.pop('has_accepted', None)
                problems_list.append(prob)
            
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
                'total_pages': (total + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user problems',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSubmissionsView(APIView):
    """
    API mới cho UserProfile - Tab Submissions
    Trả về tất cả submissions của user (cả practice và contest) với phân trang
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Lấy tất cả submissions của user
            submissions = Submissions.objects.filter(user=user).select_related(
                'problem', 'language', 'contest'
            ).order_by('-submitted_at')
            
            # Count total
            total = submissions.count()
            
            # Pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_submissions = submissions[start_idx:end_idx]
            
            # Format response
            submissions_data = []
            for sub in paginated_submissions:
                # Tìm contest_problem_id nếu có
                contest_problem_id = None
                if sub.contest:
                    from contests.models import ContestProblem
                    contest_problem = ContestProblem.objects.filter(
                        contest=sub.contest,
                        problem=sub.problem
                    ).first()
                    if contest_problem:
                        contest_problem_id = contest_problem.id
                
                submissions_data.append({
                    'id': sub.id,
                    'problem_id': sub.problem.id,
                    'problem_title': sub.problem.title,
                    'problem_slug': sub.problem.slug,
                    'language_id': sub.language.id if sub.language else None,
                    'language_name': sub.language.name if sub.language else 'Unknown',
                    'status': normalize_status(sub.status),
                    'score': float(sub.score) if sub.score else None,
                    'submitted_at': sub.submitted_at.isoformat(),
                    'contest_id': sub.contest.id if sub.contest else None,
                    'contest_title': sub.contest.title if sub.contest else None,
                    'contest_problem_id': contest_problem_id,
                })
            
            return Response({
                'submissions': submissions_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user submissions',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRegisteredContestsView(APIView):
    """
    API mới cho UserProfile - Tab Contests
    Trả về danh sách contests mà user đã đăng ký tham gia với phân trang
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            from contests.models import ContestParticipant, Contest
            
            # Lấy các contests mà user đã đăng ký, loại bỏ contest practice
            participants = ContestParticipant.objects.filter(
                user=user
            ).exclude(
                contest__slug='practice'
            ).select_related('contest').order_by('-registered_at')
            
            # Count total
            total = participants.count()
            
            # Pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_participants = participants[start_idx:end_idx]
            
            # Format response
            contests_data = []
            for participant in paginated_participants:
                contest = participant.contest
                contests_data.append({
                    'id': contest.id,
                    'slug': contest.slug,
                    'title': contest.title,
                    'start_at': contest.start_at.isoformat(),
                    'end_at': contest.end_at.isoformat(),
                    'registration_date': participant.registered_at.isoformat(),
                    'is_active': participant.is_active,
                })
            
            return Response({
                'contests': contests_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user contests',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserStatisticsView(APIView):
    """
    API mới cho UserProfile - Statistics tổng hợp
    Trả về các thống kê đã tính toán sẵn:
    - total_submissions: Tổng số submissions
    - accepted_submissions: Số submissions AC
    - acceptance_rate: Tỷ lệ AC (%)
    - problems_solved: Số problems đã giải (AC)
    - contests_participated: Số contests đã tham gia
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Lấy tất cả submissions của user
            all_submissions = Submissions.objects.filter(user=user)
            
            # Tính total submissions
            total_submissions = all_submissions.count()
            
            # Tính accepted submissions
            accepted_submissions = all_submissions.filter(
                status__iexact='AC'
            ).count()
            
            # Tính acceptance rate
            acceptance_rate = round((accepted_submissions / total_submissions * 100), 2) if total_submissions > 0 else 0
            
            # Tính problems solved (unique problems có AC)
            problems_solved = all_submissions.filter(
                status__iexact='AC'
            ).values('problem').distinct().count()
            
            # Tính contests participated (unique contests đã submit, loại bỏ practice)
            contests_participated = all_submissions.filter(
                contest__isnull=False
            ).exclude(
                contest__slug='practice'
            ).values('contest').distinct().count()
            
            return Response({
                'total_submissions': total_submissions,
                'accepted_submissions': accepted_submissions,
                'acceptance_rate': acceptance_rate,
                'problems_solved': problems_solved,
                'contests_participated': contests_participated
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch user statistics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
