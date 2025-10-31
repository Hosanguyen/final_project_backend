from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Problem, TestCase
from .serializers import (
    ProblemListSerializer, ProblemDetailSerializer,
    ProblemCreateSerializer, ProblemUpdateSerializer,
    TestCaseSerializer, TestCaseCreateSerializer
)
from .domjudge_service import DOMjudgeService
from common.authentication import CustomJWTAuthentication


class ProblemListCreateView(APIView):
    """
    GET: List all problems (with filters)
    POST: Create new problem + Auto sync to DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        problems = Problem.objects.all()
        
        # Filters
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
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        problems = problems.order_by(ordering)
        
        # Pagination
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
        serializer = ProblemCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo problem
        problem = serializer.save(created_by=request.user)
        
        # Auto sync to DOMjudge nếu có test cases
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
    DELETE: Delete problem + Delete from DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        problem = get_object_or_404(Problem, id=id)
        serializer = ProblemDetailSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, id):
        problem = get_object_or_404(Problem, id=id)
        serializer = ProblemUpdateSerializer(problem, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update problem
        problem = serializer.save(updated_by=request.user)
        
        # Auto re-sync to DOMjudge nếu đã sync trước đó
        sync_status = "not_synced"
        sync_message = ""
        
        if problem.is_synced_to_domjudge and problem.test_cases.exists():
            try:
                domjudge_service = DOMjudgeService()
                domjudge_problem_id = domjudge_service.sync_problem(problem)
                
                problem.domjudge_problem_id = domjudge_problem_id
                problem.last_synced_at = timezone.now()
                problem.save()
                
                sync_status = "re_synced"
                sync_message = "Re-synced to DOMjudge successfully"
            
            except Exception as e:
                sync_status = "sync_failed"
                sync_message = str(e)
        
        detail_serializer = ProblemDetailSerializer(problem)
        
        return Response({
            "detail": "Problem updated successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        })
    
    def delete(self, request, id):
        problem = get_object_or_404(Problem, id=id)
        
        # Xóa từ DOMjudge trước
        if problem.is_synced_to_domjudge and problem.domjudge_problem_id:
            try:
                domjudge_service = DOMjudgeService()
                domjudge_service.delete_problem(problem.domjudge_problem_id)
            except Exception as e:
                print(f"Warning: Failed to delete from DOMjudge: {str(e)}")
        
        # Xóa từ Django
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
        problem = get_object_or_404(Problem, id=problem_id)
        test_cases = problem.test_cases.all()
        serializer = TestCaseSerializer(test_cases, many=True)
        
        return Response({
            "problem_id": problem.id,
            "problem_title": problem.title,
            "test_cases": serializer.data
        })
    
    def post(self, request, problem_id):
        problem = get_object_or_404(Problem, id=problem_id)
        serializer = TestCaseCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo test case
        test_case = serializer.save(problem=problem)
        
        # Auto sync to DOMjudge
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
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        serializer = TestCaseSerializer(test_case)
        return Response(serializer.data)
    
    def put(self, request, problem_id, testcase_id):
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        serializer = TestCaseCreateSerializer(test_case, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update test case
        test_case = serializer.save()
        problem = test_case.problem
        
        # Auto re-sync
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
        test_case = get_object_or_404(TestCase, id=testcase_id, problem_id=problem_id)
        problem = test_case.problem
        
        # Xóa test case
        test_case.delete()
        
        # Auto re-sync
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
        problem = get_object_or_404(Problem, id=id)
        
        # TODO: Implement statistics từ Submission model
        stats = {
            "problem_id": problem.id,
            "problem_title": problem.title,
            "is_synced_to_domjudge": problem.is_synced_to_domjudge,
            "last_synced_at": problem.last_synced_at,
            "test_case_count": problem.test_cases.count(),
        }
        
        return Response(stats)


class SubmissionCreateView(APIView):
    """
    POST: Submit code to problem
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, problem_id):
        from .models import Submissions
        from course.models import Language
        from .serializers import SubmissionCreateSerializer, SubmissionSerializer
        
        problem = get_object_or_404(Problem, id=problem_id)
        
        # Validate input
        serializer = SubmissionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        language_id = serializer.validated_data['language_id']
        code = serializer.validated_data['code']
        
        # Kiểm tra language có được phép không
        language = get_object_or_404(Language, id=language_id)
        if problem.allowed_languages.exists() and language not in problem.allowed_languages.all():
            return Response({
                "error": f"Ngôn ngữ {language.name} không được phép cho bài này"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra problem đã sync với DOMjudge chưa
        if not problem.is_synced_to_domjudge or not problem.domjudge_problem_id:
            return Response({
                "error": "Problem chưa được đồng bộ với DOMjudge"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo submission trong DB
        submission = Submissions.objects.create(
            problem=problem,
            user=request.user,
            language=language,
            code_text=code,
            status="pending"
        )
        
        # Submit lên DOMjudge
        try:
            domjudge_service = DOMjudgeService()
            contest_id = request.data.get('contest_id') or 'practice'  # Optional
            team_id = request.data.get('team_id') or 'exteam'  # Optional
            domjudge_response = domjudge_service.submit_code(
                problem=problem,
                language=language,
                source_code=code,
                contest_id=contest_id,
                team_id=team_id
            )
            
            # Lưu submission ID từ DOMjudge
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
            # Đánh dấu submission failed
            submission.status = "error"
            submission.feedback = str(e)
            submission.save()
            
            return Response({
                "error": f"Submit to DOMjudge failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmissionListView(APIView):
    """
    GET: List submissions for a problem (or all submissions by user)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_id=None):
        from .models import Submissions
        from .serializers import SubmissionListSerializer
        
        if problem_id:
            submissions = Submissions.objects.filter(problem_id=problem_id)
        else:
            submissions = Submissions.objects.all()
        
        # Filter by user (chỉ xem submission của mình, trừ admin)
        if not request.user.is_staff:
            submissions = submissions.filter(user=request.user)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-submitted_at')
        submissions = submissions.order_by(ordering)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = submissions.count()
        submissions = submissions[start:end]
        
        serializer = SubmissionListSerializer(submissions, many=True)
        
        return Response({
            "results": serializer.data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        })


class SubmissionDetailView(APIView):
    """
    GET: Get submission detail and sync result from DOMjudge
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, submission_id):
        from .models import Submissions
        from .serializers import SubmissionSerializer
        
        submission = get_object_or_404(Submissions, id=submission_id)
        
        # Check permission (chỉ xem submission của mình hoặc admin)
        if not request.user.is_staff and submission.user != request.user:
            return Response({
                "error": "Bạn không có quyền xem submission này"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Nếu submission đang judging, lấy kết quả mới nhất từ DOMjudge
        if submission.status == "judging" and submission.domjudge_submission_id:
            try:
                domjudge_service = DOMjudgeService()
                result = domjudge_service.get_submission_result(submission.domjudge_submission_id)
                
                # Cập nhật status và feedback
                # Tùy vào response của DOMjudge
                if 'judgement_type_id' in result:
                    submission.status = result.get('judgement_type_id', 'unknown')
                
                submission.save()
            
            except Exception as e:
                print(f"Failed to sync submission result: {str(e)}")
        
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data)