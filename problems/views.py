import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Problem, TestCase, Submissions
from .serializers import (
    ProblemListSerializer, ProblemDetailSerializer,
    ProblemCreateSerializer, ProblemUpdateSerializer,
    TestCaseSerializer, TestCaseCreateSerializer
)
from .domjudge_service import DOMjudgeService
from contests.domjudge_service import DOMjudgeContestService
from contests.models import ContestProblem, Contest
from common.authentication import CustomJWTAuthentication



class ProblemListCreateView(APIView):
    """
    GET: List all problems (with filters)
    POST: Create new problem + Auto sync to DOMjudge
    Hỗ trợ 2 mode:
    - Manual: Gửi test_cases array
    - ZIP: Gửi test_cases_zip file
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.has_perm('problems.read'):
            return Response(
                {"detail": "Bạn không có quyền xem danh sách problems. Yêu cầu quyền: problems.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        problems = Problem.objects.all()
        
        difficulty = request.query_params.get('difficulty')
        is_public = request.query_params.get('is_public')
        tag_id = request.query_params.get('tag_id')
        search = request.query_params.get('search')
        
        if difficulty:
            problems = problems.filter(difficulty=difficulty)
        
        if is_public is not None:
            problems = problems.filter(is_public=is_public.lower() == 'true')
        
        if tag_id:
            problems = problems.filter(tags__id=tag_id)
        
        if search:
            problems = problems.filter(
                Q(title__icontains=search) |
                Q(short_statement__icontains=search) |
                Q(slug__icontains=search)
            )
        
        ordering = request.query_params.get('ordering', '-created_at')
        problems = problems.order_by(ordering)
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = problems.count()
        problems = problems[start:end]
        
        serializer = ProblemListSerializer(problems, many=True)
        
        return Response({
            "results": serializer.data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        })
    
    def post(self, request):
        if not request.user.has_perm('problems.create'):
            return Response(
                {"detail": "Bạn không có quyền tạo problem. Yêu cầu quyền: problems.create"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.dict()
        
        if 'test_cases' in data:
            try:
                test_cases_json = data.pop('test_cases')
                data['test_cases'] = json.loads(test_cases_json)
            except json.JSONDecodeError as e:
                return Response({
                    'test_cases': f'Invalid JSON: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if 'tag_ids' in request.data:
            tag_ids = request.data.getlist('tag_ids')
            if tag_ids:
                data['tag_ids'] = [int(x) for x in tag_ids if x]
        
        if 'language_ids' in request.data:
            lang_ids = request.data.getlist('language_ids')
            if lang_ids:
                data['language_ids'] = [int(x) for x in lang_ids if x]

        serializer = ProblemCreateSerializer(data=data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        problem = serializer.save(created_by=request.user)
        
        sync_status = "not_synced"
        sync_message = ""
        zip_process_result = None
        
        if problem.test_cases.exists():
            try:
                domjudge_service = DOMjudgeService()
                domjudge_problem_id = domjudge_service.sync_problem(problem)
                
                problem.domjudge_problem_id = domjudge_problem_id
                problem.is_synced_to_domjudge = True
                problem.last_synced_at = timezone.now()
                problem.save()


                contest = Contest.objects.filter(slug='practice').first()
                max_sequence = ContestProblem.objects.filter(contest=contest).count()

                domjudge_contest_service = DOMjudgeContestService()
                if problem.is_public:
                    contest_problem = ContestProblem.objects.create(
                        contest=contest,
                        problem=problem,
                        alias=problem.slug,
                        point=1,
                        sequence=max_sequence,
                        label=problem.slug,
                        lazy_eval_results=False
                    )
                    domjudge_contest_service.add_problem_to_contest('practice', problem.slug, {
                        'label': problem.slug,
                        'lazy_eval_results': 0,
                        'points': 1
                    })
                
                sync_status = "synced"
                sync_message = f"Synced to DOMjudge with ID: {domjudge_problem_id}"
            
            except Exception as e:
                sync_status = "sync_failed"
                sync_message = str(e)
        else:
            sync_message = "No test cases to sync"
        
        detail_serializer = ProblemDetailSerializer(problem)
        
        return Response({
            "detail": "Problem created successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        }, status=status.HTTP_201_CREATED)


class ProblemDetailView(APIView):
    """
    GET: Get problem detail
    PUT: Update problem + Auto re-sync to DOMjudge
         Hỗ trợ update test cases bằng ZIP (sẽ XÓA cũ và THAY THẾ)
    DELETE: Delete problem + Delete from DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        if not request.user.has_perm('problems.read'):
            return Response(
                {"detail": "Bạn không có quyền xem chi tiết problem. Yêu cầu quyền: problems.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        problem = get_object_or_404(Problem, id=id)
        serializer = ProblemDetailSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, id):
        if not request.user.has_perm('problems.update'):
            return Response(
                {"detail": "Bạn không có quyền cập nhật problem. Yêu cầu quyền: problems.update"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        problem = get_object_or_404(Problem, id=id)
        data = request.data.dict()
        
        if 'test_cases' in data:
            try:
                test_cases_json = data.pop('test_cases')
                data['test_cases'] = json.loads(test_cases_json)
            except json.JSONDecodeError as e:
                return Response({
                    'test_cases': f'Invalid JSON: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if 'tag_ids' in request.data:
            tag_ids = request.data.getlist('tag_ids')
            if tag_ids:
                data['tag_ids'] = [int(x) for x in tag_ids if x]
        
        if 'language_ids' in request.data:
            lang_ids = request.data.getlist('language_ids')
            if lang_ids:
                data['language_ids'] = [int(x) for x in lang_ids if x]
        
        serializer = ProblemUpdateSerializer(problem, data=data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        problem = serializer.save(updated_by=request.user)
        
        sync_status = "not_synced"
        sync_message = ""
        
        if problem.test_cases.exists():
            try:
                domjudge_service = DOMjudgeService()
                domjudge_problem_id = domjudge_service.sync_problem(problem)
                
                problem.domjudge_problem_id = domjudge_problem_id
                problem.is_synced_to_domjudge = True
                problem.last_synced_at = timezone.now()
                problem.save()
                
                sync_status = "re_synced"
                sync_message = "Re-synced to DOMjudge successfully"
            
            except Exception as e:
                sync_status = "sync_failed"
                sync_message = str(e)
        
        domjudge_contest_service = DOMjudgeContestService()
        contest = Contest.objects.filter(slug='practice').first()
        max_sequence = ContestProblem.objects.filter(contest=contest).count()

        if problem.is_public:
            try:
                contest_problem, created = ContestProblem.objects.get_or_create(
                    contest=contest,
                    problem=problem,
                    defaults={
                        'alias': problem.slug,
                        'point': 1,
                        'sequence': max_sequence,
                        'label': problem.slug,
                        'lazy_eval_results': False
                    }
                )
                if created:
                    domjudge_contest_service.add_problem_to_contest('practice', problem.slug, {
                        'label': problem.slug,
                        'lazy_eval_results': 0,
                        'points': 1
                    })
            except Exception as e:
                print(f"Warning: Failed to add/update problem in practice contest: {str(e)}")
        elif problem.is_public == False:
            try:
                contest_problem = ContestProblem.objects.get(contest=contest, problem=problem)
                if contest_problem:
                    contest_problem.delete()
                    domjudge_contest_service.remove_problem_from_contest('practice', problem.slug)
            except Exception as e:
                print(f"Warning: Failed to remove problem from practice contest: {str(e)}")
        
        detail_serializer = ProblemDetailSerializer(problem)
        
        return Response({
            "detail": "Problem updated successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        })
    
    def delete(self, request, id):
        if not request.user.has_perm('problems.delete'):
            return Response(
                {"detail": "Bạn không có quyền xóa problem. Yêu cầu quyền: problems.delete"},
                status=status.HTTP_403_FORBIDDEN
            )
        problem = get_object_or_404(Problem, id=id)
        
        if problem.is_synced_to_domjudge and problem.domjudge_problem_id:
            try:
                domjudge_service = DOMjudgeService()
                domjudge_service.delete_problem(problem.domjudge_problem_id)
            except Exception as e:
                print(f"Warning: Failed to delete from DOMjudge: {str(e)}")
        
        problem.delete()
        
        return Response({
            "detail": "Problem deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)


class ProblemTestCasesView(APIView):
    """
    GET: List test cases for a problem
    POST: Add test case + Auto sync to DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id):
        if not request.user.has_perm('test_cases.read'):
            return Response(
                {"detail": "Bạn không có quyền xem test cases. Yêu cầu quyền: test_cases.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        problem = get_object_or_404(Problem, id=problem_id)
        test_cases = problem.test_cases.all()
        serializer = TestCaseSerializer(test_cases, many=True)
        
        return Response({
            "problem_id": problem.id,
            "problem_title": problem.title,
            "test_cases": serializer.data
        })
    
    def post(self, request, problem_id):
        if not request.user.has_perm('test_cases.create'):
            return Response(
                {"detail": "Bạn không có quyền tạo test case. Yêu cầu quyền: test_cases.create"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        problem = get_object_or_404(Problem, id=problem_id)
        serializer = TestCaseCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_case = serializer.save(problem=problem)
        
        sync_status = "not_synced"
        sync_message = ""
        
        try:
            domjudge_service = DOMjudgeService()
            domjudge_problem_id = domjudge_service.sync_problem(problem)
            
            problem.domjudge_problem_id = domjudge_problem_id
            problem.is_synced_to_domjudge = True
            problem.last_synced_at = timezone.now()
            problem.save()
            
            sync_status = "synced"
            sync_message = "Test case added and synced to DOMjudge"
        
        except Exception as e:
            sync_status = "sync_failed"
            sync_message = str(e)
        
        detail_serializer = TestCaseSerializer(test_case)
        
        return Response({
            "detail": "Test case added successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        }, status=status.HTTP_201_CREATED)


class TestCaseDetailView(APIView):
    """
    GET: Get test case detail
    PUT: Update test case + Auto re-sync to DOMjudge
    DELETE: Delete test case + Auto re-sync to DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id, testcase_id):
        if not request.user.has_perm('test_cases.read'):
            return Response(
                {"detail": "Bạn không có quyền xem test case. Yêu cầu quyền: test_cases.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        serializer = TestCaseSerializer(test_case)
        return Response(serializer.data)
    
    def put(self, request, problem_id, testcase_id):
        if not request.user.has_perm('test_cases.update'):
            return Response(
                {"detail": "Bạn không có quyền cập nhật test case. Yêu cầu quyền: test_cases.update"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        serializer = TestCaseCreateSerializer(test_case, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_case = serializer.save()
        problem = test_case.problem
        
        sync_status = "not_synced"
        sync_message = ""
        
        if problem.is_synced_to_domjudge:
            try:
                domjudge_service = DOMjudgeService()
                domjudge_service.sync_problem(problem)
                problem.last_synced_at = timezone.now()
                problem.save()
                
                sync_status = "re_synced"
                sync_message = "Re-synced to DOMjudge"
            except Exception as e:
                sync_status = "sync_failed"
                sync_message = str(e)
        
        detail_serializer = TestCaseSerializer(test_case)
        
        return Response({
            "detail": "Test case updated successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        })
    
    def delete(self, request, problem_id, testcase_id):
        if not request.user.has_perm('test_cases.delete'):
            return Response(
                {"detail": "Bạn không có quyền xóa test case. Yêu cầu quyền: test_cases.delete"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        problem = test_case.problem
        
        test_case.delete()
        
        if problem.is_synced_to_domjudge and problem.test_cases.exists():
            try:
                domjudge_service = DOMjudgeService()
                domjudge_service.sync_problem(problem)
                problem.last_synced_at = timezone.now()
                problem.save()
            except Exception as e:
                print(f"Warning: Re-sync failed: {str(e)}")
        
        return Response({
            "detail": "Test case deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)


class ProblemStatisticsView(APIView):
    """GET: Get problem statistics"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        if not request.user.has_perm('problems.read'):
            return Response(
                {"detail": "Bạn không có quyền xem thống kê problem. Yêu cầu quyền: problems.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        from contests.models import Contest, ContestProblem
        from django.db.models import Count, Avg, Max, Min
        from datetime import datetime, timedelta
        
        problem = get_object_or_404(Problem, id=id)
        contest_id = request.query_params.get('contest_id')
        
        submissions_qs = Submissions.objects.filter(problem=problem)
        
        if contest_id:
            submissions_qs = submissions_qs.filter(contest_id=contest_id)
        
        total_submissions = submissions_qs.count()
        
        by_status = list(submissions_qs.values('status')
                        .annotate(count=Count('id'))
                        .order_by('-count'))
        
        accepted_submissions = submissions_qs.filter(status='correct').count()
        acceptance_rate = round((accepted_submissions / total_submissions * 100), 2) if total_submissions > 0 else 0
        
        unique_solvers = submissions_qs.filter(status='correct').values('user').distinct().count()
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        submissions_by_date = submissions_qs.filter(
            submitted_at__gte=thirty_days_ago
        ).extra(
            select={'date': 'DATE(submitted_at)'}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        top_solvers = list(
            submissions_qs.filter(status='correct')
            .values('user__username', 'user__full_name')
            .annotate(
                ac_count=Count('id'),
                first_ac=Min('submitted_at')
            )
            .order_by('-ac_count', 'first_ac')[:10]
        )
        
        contests_list = []
        if not contest_id:
            contest_problems = ContestProblem.objects.filter(problem=problem).select_related('contest')
            for cp in contest_problems:
                contest_submissions = Submissions.objects.filter(problem=problem, contest=cp.contest)
                contest_ac = contest_submissions.filter(status='correct').count()
                contest_total = contest_submissions.count()
                
                contests_list.append({
                    'contest_id': cp.contest.id,
                    'contest_title': cp.contest.title,
                    'alias': cp.alias,
                    'point': float(cp.point),
                    'total_submissions': contest_total,
                    'accepted_submissions': contest_ac,
                })
        
        stats = {
            "problem_id": problem.id,
            "problem_title": problem.title,
            "contest_id": contest_id,
            "is_synced_to_domjudge": problem.is_synced_to_domjudge,
            "last_synced_at": problem.last_synced_at,
            "test_case_count": problem.test_cases.count(),
            "total_submissions": total_submissions,
            "accepted_submissions": accepted_submissions,
            "acceptance_rate": acceptance_rate,
            "unique_solvers": unique_solvers,
            "by_status": by_status,
            "submissions_by_date": list(submissions_by_date),
            "top_solvers": top_solvers,
            "contests": contests_list,
        }
        
        return Response(stats)


class SubmissionCreateView(APIView):
    """
    POST: Submit code to problem
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, problem_id):
        if not request.user.has_perm('submissions.create'):
            return Response(
                {"detail": "Bạn không có quyền submit code. Yêu cầu quyền: submissions.create"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import Submissions
        from course.models import Language
        from .serializers import SubmissionCreateSerializer, SubmissionSerializer
        
        problem = get_object_or_404(Problem, id=problem_id)
        
        serializer = SubmissionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        language_id = serializer.validated_data['language_id']
        code = serializer.validated_data['code']
        contest_id = serializer.validated_data.get('contest_id')
        
        language = get_object_or_404(Language, id=language_id)
        if problem.allowed_languages.exists() and language not in problem.allowed_languages.all():
            return Response({
                "error": f"Ngôn ngữ {language.name} không được phép cho bài này"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not problem.is_synced_to_domjudge or not problem.domjudge_problem_id:
            return Response({
                "error": "Problem chưa được đồng bộ với DOMjudge"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        contest = None
        if contest_id:
            from contests.models import Contest
            contest = get_object_or_404(Contest, id=contest_id)
        
        submission = Submissions.objects.create(
            problem=problem,
            user=request.user,
            language=language,
            contest=contest,
            code_text=code,
            status="pending"
        )
        
        try:
            domjudge_service = DOMjudgeService()
            contest_id = contest.slug or 'practice'
            team_id = request.data.get('team_id') or 'exteam'
            domjudge_response = domjudge_service.submit_code(
                problem=problem,
                language=language,
                source_code=code,
                contest_id=contest_id,
                team_id=team_id
            )
            
            submission.domjudge_submission_id = domjudge_response.get('id') or domjudge_response.get('submitid')
            submission.status = "judging"
            submission.save()
            
            result_serializer = SubmissionSerializer(submission)
            
            return Response({
                "detail": "Code submitted successfully",
                "submission": result_serializer.data,
                "domjudge_response": domjudge_response
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            submission.status = "error"
            submission.feedback = str(e)
            submission.save()
            
            error_message = str(e)
            user_friendly_message = "Không thể kết nối đến hệ thống chấm bài. Vui lòng thử lại sau."
            
            if "Connection" in error_message or "connection" in error_message:
                user_friendly_message = "Hệ thống chấm bài tạm thời không khả dụng. Vui lòng thử lại sau."
            elif "timeout" in error_message.lower():
                user_friendly_message = "Kết nối đến hệ thống chấm bài quá chậm. Vui lòng thử lại."
            elif "401" in error_message or "403" in error_message:
                user_friendly_message = "Lỗi xác thực với hệ thống chấm bài. Vui lòng liên hệ quản trị viên."
            elif "404" in error_message:
                user_friendly_message = "Không tìm thấy bài toán trên hệ thống chấm bài."
            elif "500" in error_message:
                user_friendly_message = "Hệ thống chấm bài gặp lỗi nội bộ. Vui lòng thử lại sau."
            
            return Response({
                "error": user_friendly_message
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmissionListView(APIView):
    """
    GET: List submissions for a problem (or all submissions by user)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id=None):
        if not request.user.has_perm('submissions.read'):
            return Response(
                {"detail": "Bạn không có quyền xem submissions. Yêu cầu quyền: submissions.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import Submissions
        from .serializers import SubmissionListSerializer
        from contests.models import Contest
        
        if problem_id:
            submissions = Submissions.objects.filter(problem_id=problem_id)
        else:
            submissions = Submissions.objects.all()

        contest_id = request.query_params.get('contest_id')
        if contest_id:
            submissions = submissions.filter(contest_id=contest_id)
        else:
            practice_contests = Contest.objects.filter(slug='practice').values_list('id', flat=True)
            submissions = submissions.filter(
                Q(contest_id__isnull=True) | Q(contest_id__in=practice_contests)
            )
        
        if not request.user.is_staff:
            submissions = submissions.filter(user=request.user)
        
        sync_from_domjudge = request.query_params.get('sync', 'true').lower() == 'true'
        if sync_from_domjudge:
            self._sync_submissions_status(submissions)
        
        ordering = request.query_params.get('ordering', '-submitted_at')
        submissions = submissions.order_by(ordering)
        
        all_completed = not submissions.filter(status__in=['judging', 'pending']).exists()
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = submissions.count()
        submissions_page = submissions[start:end]
        
        serializer = SubmissionListSerializer(submissions_page, many=True)
        
        return Response({
            "results": serializer.data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "all_completed": all_completed
        })
    
    def _sync_submissions_status(self, submissions):
        domjudge_service = DOMjudgeService()
        contest_id = None
        
        for submission in submissions.filter(status='judging'):
            if submission.domjudge_submission_id:
                try:
                    judgement = domjudge_service.get_judgement_summary(
                        submission.domjudge_submission_id
                    )
                    
                    if judgement and judgement.get('valid'):
                        judgement_type = judgement.get('judgement_type_id', 'unknown')
                        submission.status = judgement_type.lower()
                        
                        try:
                            detailed_results = domjudge_service.get_detailed_judging_results(
                                submission.domjudge_submission_id
                            )
                            
                            if detailed_results and 'test_cases' in detailed_results:
                                test_cases = detailed_results['test_cases']
                                submission.test_total = len(test_cases)
                                submission.test_passed = sum(
                                    1 for tc in test_cases 
                                    if tc.get('verdict', '').lower() == 'correct'
                                )
                        except Exception as e:
                            print(f"Failed to get detailed results: {str(e)}")
                        
                        if judgement_type == 'AC':
                            submission.score = 100.00
                        else:
                            submission.score = 0.00
                        
                        submission.feedback = f"Max run time: {judgement.get('max_run_time', 0)}s"
                        submission.save()
                        
                        if submission.contest:
                            from contests.ranking_service import ContestRankingService
                            try:
                                ContestRankingService.update_user_ranking(
                                    submission.contest.id,
                                    submission.user.id
                                )
                            except Exception as e:
                                print(f"Failed to update ranking: {str(e)}")
                
                except Exception as e:
                    print(f"Failed to sync submission {submission.id}: {str(e)}")
                    continue


class SubmissionDetailView(APIView):
    """
    GET: Get submission detail and sync result from DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, submission_id):
        if not request.user.has_perm('submissions.read'):
            return Response(
                {"detail": "Bạn không có quyền xem submission. Yêu cầu quyền: submissions.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import Submissions
        from .serializers import SubmissionSerializer
        
        submission = get_object_or_404(Submissions, id=submission_id)
        
        if not request.user.is_staff and submission.user != request.user:
            return Response({
                "error": "Bạn không có quyền xem submission này"
            }, status=status.HTTP_403_FORBIDDEN)
        
        if submission.status == "judging" and submission.domjudge_submission_id:
            try:
                domjudge_service = DOMjudgeService()
                contest_id = request.query_params.get('contest_id')
                
                judgement = domjudge_service.get_judgement(
                    submission.domjudge_submission_id,
                    contest_id=contest_id
                )
                
                if judgement and judgement.get('valid'):
                    judgement_type = judgement.get('judgement_type_id', 'unknown')
                    submission.status = judgement_type.lower()
                    
                    try:
                        detailed_results = domjudge_service.get_detailed_judging_results(
                            submission.domjudge_submission_id
                        )
                        
                        if detailed_results and 'test_cases' in detailed_results:
                            test_cases = detailed_results['test_cases']
                            submission.test_total = len(test_cases)
                            submission.test_passed = sum(
                                1 for tc in test_cases 
                                if tc.get('verdict', '').lower() == 'correct'
                            )
                    except Exception as e:
                        print(f"Failed to get detailed results: {str(e)}")
                    
                    if judgement_type == 'AC':
                        submission.score = 100.00
                    else:
                        submission.score = 0.00
                    
                    feedback_parts = [
                        f"Judgement: {judgement_type}",
                        f"Max run time: {judgement.get('max_run_time', 0)}s",
                        f"Start time: {judgement.get('start_contest_time', 'N/A')}",
                        f"End time: {judgement.get('end_contest_time', 'N/A')}"
                    ]
                    submission.feedback = "\n".join(feedback_parts)
                    submission.save()
                    
                    # Update contest ranking if submission is for a contest
                    if submission.contest:
                        from contests.ranking_service import ContestRankingService
                        try:
                            ContestRankingService.update_user_ranking(
                                submission.contest.id,
                                submission.user.id
                            )
                        except Exception as e:
                            print(f"Failed to update ranking: {str(e)}")
            
            except Exception as e:
                print(f"Failed to sync submission result: {str(e)}")
        
        from .serializers import SubmissionDetailSerializer
        serializer = SubmissionDetailSerializer(submission)
        return Response(serializer.data)


class ProblemRecommendationView(APIView):
    """
    GET: Lấy danh sách bài toán được gợi ý cho user hiện tại
    Dựa trên model đã train và lịch sử giải bài của user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.has_perm('problems.read'):
            return Response(
                {"detail": "Bạn không có quyền xem gợi ý problems. Yêu cầu quyền: problems.read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        import os
        from django.conf import settings
        
        try:
            user = request.user
            
            n_recommendations = int(request.query_params.get('limit', 10))
            
            from common.recommender import ProductionRecommender
            recommender = ProductionRecommender(model_path='recommendation_model.pkl')
            
            if not recommender.load_model():
                return Response({
                    'error': 'Recommendation model not found. Please train the model first.',
                    'hint': 'Run: python manage.py train_recommendation'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            solved_submissions = Submissions.objects.filter(
                user=user,
                status='ac',
                contest__isnull=True
            ).values_list('problem_id', flat=True).distinct()
            
            solved_ids = list(solved_submissions)
            
            valid_problem_ids = set(
                Problem.objects.filter(
                    is_public=True,
                    is_synced_to_domjudge=True
                ).values_list('id', flat=True)
            )
            
            recommendations = recommender.recommend(
                user_id=user.id,
                solved_ids=solved_ids,
                valid_problem_ids_set=valid_problem_ids,
                n_recommendations=n_recommendations
            )
            
            if not recommendations:
                unsolved_problems = Problem.objects.filter(
                    is_public=True,
                    is_synced_to_domjudge=True
                ).exclude(id__in=solved_ids)[:n_recommendations]
                
                contest_problem_map = {
                    cp.problem_id: cp.id
                    for cp in ContestProblem.objects
                        .filter(contest__slug='practice', problem__in=unsolved_problems)
                }

                recommendations = [
                    {
                        'problem_id': p.id,
                        'title': p.title,
                        'contest_problem_id': contest_problem_map.get(p.id),
                        'difficulty': p.difficulty,
                        'rating': p.rating,
                        'tags': list(p.tags.values_list('name', flat=True)),
                        'score': 0.0
                    }
                    for p in unsolved_problems
                ]

            
            return Response({
                'user_id': user.id,
                'username': user.username,
                'user_rating': user.current_rating,
                'solved_count': len(solved_ids),
                'recommendations': recommendations
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to generate recommendations: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)