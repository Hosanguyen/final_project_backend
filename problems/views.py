import json
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
    Hỗ trợ 2 mode:
    - Manual: Gửi test_cases array
    - ZIP: Gửi test_cases_zip file
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # ... existing GET code - KHÔNG THAY ĐỔI ...
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
        data = request.data.dict()  # ← Chuyển QueryDict → dict thường
        
        # Parse test_cases từ JSON string
        if 'test_cases' in data:
            try:
                test_cases_json = data.pop('test_cases')  # ← XÓA và LẤY GIÁ TRỊ
                data['test_cases'] = json.loads(test_cases_json)  # ← THÊM LẠI đã parse
            except json.JSONDecodeError as e:
                return Response({
                    'test_cases': f'Invalid JSON: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse tag_ids (có thể là multiple values)
        if 'tag_ids' in request.data:
            tag_ids = request.data.getlist('tag_ids')
            if tag_ids:
                data['tag_ids'] = [int(x) for x in tag_ids if x]
        
        # Parse language_ids (tương tự)
        if 'language_ids' in request.data:
            lang_ids = request.data.getlist('language_ids')
            if lang_ids:
                data['language_ids'] = [int(x) for x in lang_ids if x]
        

        # if 'test_cases' in data:
        #     try:
        #         data['test_cases'] = json.loads(request.data['test_cases'])
        #     except json.JSONDecodeError:
        #         return Response({'test_cases': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
        
        # return Response({"detail": request.data}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProblemCreateSerializer(data=data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo problem (đã bao gồm test cases từ manual hoặc ZIP)
        problem = serializer.save(created_by=request.user)
        
        # Auto sync to DOMjudge
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
        # ... existing GET code - KHÔNG THAY ĐỔI ...
        problem = get_object_or_404(Problem, id=id)
        serializer = ProblemDetailSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, id):
        problem = get_object_or_404(Problem, id=id)
        data = request.data.dict()  # ← Chuyển QueryDict → dict thường
        
        # Parse test_cases từ JSON string
        if 'test_cases' in data:
            try:
                test_cases_json = data.pop('test_cases')  # ← XÓA và LẤY GIÁ TRỊ
                data['test_cases'] = json.loads(test_cases_json)  # ← THÊM LẠI đã parse
            except json.JSONDecodeError as e:
                return Response({
                    'test_cases': f'Invalid JSON: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse tag_ids (có thể là multiple values)
        if 'tag_ids' in request.data:
            tag_ids = request.data.getlist('tag_ids')
            if tag_ids:
                data['tag_ids'] = [int(x) for x in tag_ids if x]
        
        # Parse language_ids (tương tự)
        if 'language_ids' in request.data:
            lang_ids = request.data.getlist('language_ids')
            if lang_ids:
                data['language_ids'] = [int(x) for x in lang_ids if x]
        
        serializer = ProblemUpdateSerializer(problem, data=data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update problem (bao gồm cả test cases từ ZIP nếu có)
        problem = serializer.save(updated_by=request.user)
        
        # Auto re-sync to DOMjudge
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
        
        detail_serializer = ProblemDetailSerializer(problem)
        
        return Response({
            "detail": "Problem updated successfully",
            "sync_status": sync_status,
            "sync_message": sync_message,
            "data": detail_serializer.data
        })
    
    def delete(self, request, id):
        # ... existing DELETE code - KHÔNG THAY ĐỔI ...
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
        contest_id = serializer.validated_data.get('contest_id')
        
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
        
        # Lấy contest object nếu có
        contest = None
        if contest_id:
            from contests.models import Contest
            contest = get_object_or_404(Contest, id=contest_id)
        
        # Tạo submission trong DB
        submission = Submissions.objects.create(
            problem=problem,
            user=request.user,
            language=language,
            contest=contest,
            code_text=code,
            status="pending"
        )
        
        # Submit lên DOMjudge
        try:
            domjudge_service = DOMjudgeService()
            contest_id = contest.slug or 'practice'  # Optional
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
        from contests.models import Contest
        
        if problem_id:
            submissions = Submissions.objects.filter(problem_id=problem_id)
        else:
            submissions = Submissions.objects.all()
        
        # Filter by contest if provided

        contest_id = request.query_params.get('contest_id')
        if contest_id:
            submissions = submissions.filter(contest_id=contest_id)
        else:
            # Nếu không truyền contest_id, lọc submissions có contest_id rỗng hoặc contest có slug là "practice"
            practice_contests = Contest.objects.filter(slug='practice').values_list('id', flat=True)
            submissions = submissions.filter(
                Q(contest_id__isnull=True) | Q(contest_id__in=practice_contests)
            )
        
        # Filter by user (chỉ xem submission của mình, trừ admin)
        if not request.user.is_staff:
            submissions = submissions.filter(user=request.user)
        
        # Sync status from DOMjudge cho các submission đang judging
        sync_from_domjudge = request.query_params.get('sync', 'true').lower() == 'true'
        if sync_from_domjudge:
            self._sync_submissions_status(submissions)
        
        # Ordering
        ordering = request.query_params.get('ordering', '-submitted_at')
        submissions = submissions.order_by(ordering)
        
        # Kiểm tra xem tất cả submissions đã hoàn thành judging chưa (trước khi pagination)
        all_completed = not submissions.filter(status__in=['judging', 'pending']).exists()
        
        # Pagination
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
            "all_completed": all_completed  # Flag để frontend biết khi nào dừng polling
        })
    
    def _sync_submissions_status(self, submissions):
        """Sync status từ DOMjudge cho các submission đang judging"""
        domjudge_service = DOMjudgeService()
        contest_id = None  # Có thể lấy từ settings hoặc request params
        
        for submission in submissions.filter(status='judging'):
            if submission.domjudge_submission_id:
                try:
                    # Lấy judgement từ DOMjudge
                    judgement = domjudge_service.get_judgement_summary(
                        submission.domjudge_submission_id
                    )
                    
                    if judgement and judgement.get('valid'):
                        # Cập nhật status từ judgement_type_id
                        judgement_type = judgement.get('judgement_type_id', 'unknown')
                        submission.status = judgement_type.lower()
                        
                        # Lấy chi tiết test cases để tính test_passed và test_total
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
                        
                        # Cập nhật score (nếu AC thì 100, không thì 0)
                        if judgement_type == 'AC':
                            submission.score = 100.00
                        else:
                            submission.score = 0.00
                        
                        # Cập nhật feedback
                        submission.feedback = f"Max run time: {judgement.get('max_run_time', 0)}s"
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
                    print(f"Failed to sync submission {submission.id}: {str(e)}")
                    continue


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
                contest_id = request.query_params.get('contest_id')
                
                # Lấy judgement từ DOMjudge
                judgement = domjudge_service.get_judgement(
                    submission.domjudge_submission_id,
                    contest_id=contest_id
                )
                
                if judgement and judgement.get('valid'):
                    # Cập nhật status từ judgement_type_id
                    judgement_type = judgement.get('judgement_type_id', 'unknown')
                    submission.status = judgement_type.lower()
                    
                    # Lấy chi tiết test cases để tính test_passed và test_total
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
                    
                    # Cập nhật score
                    if judgement_type == 'AC':
                        submission.score = 100.00
                    else:
                        submission.score = 0.00
                    
                    # Cập nhật feedback với chi tiết từ judgement
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