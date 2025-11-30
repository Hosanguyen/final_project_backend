from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json

from common.authentication import CustomJWTAuthentication
from .models import Quiz, QuizQuestion, QuizOption, QuizSubmission, QuizAnswer
from .serializers import (
    QuizListSerializer, QuizDetailSerializer,
    QuizCreateSerializer, QuizUpdateSerializer,
    QuizSubmissionSerializer, QuizSubmissionCreateSerializer,
    QuizAnswerSubmitSerializer
)


# ============================================================
# QUIZ CRUD VIEWS
# ============================================================

class QuizListView(APIView):
    """
    GET: Lấy danh sách quizzes
    POST: Tạo quiz mới (với questions)
    """
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request):
        quizzes = Quiz.objects.all().order_by('-created_at')
        serializer = QuizListSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = QuizCreateSerializer(data=request.data)
        if serializer.is_valid():
            quiz = serializer.save(created_by=request.user)
            detail_serializer = QuizDetailSerializer(quiz)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuizDetailView(APIView):
    """
    GET: Lấy chi tiết quiz
    PUT: Cập nhật quiz (bao gồm cả questions)
    DELETE: Xóa quiz
    """
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        serializer = QuizDetailSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        serializer = QuizUpdateSerializer(quiz, data=request.data)
        if serializer.is_valid():
            quiz = serializer.save()
            detail_serializer = QuizDetailSerializer(quiz)
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        quiz.delete()
        return Response(
            {"message": "Quiz deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# ============================================================
# QUIZ SUBMISSION VIEWS
# ============================================================

class QuizSubmissionStartView(APIView):
    """
    POST: Bắt đầu làm bài quiz (tạo submission với snapshot)
    """
    authentication_classes = [CustomJWTAuthentication]

    def post(self, request):
        serializer = QuizSubmissionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        quiz_id = serializer.validated_data['quiz_id']
        lesson_id = serializer.validated_data.get('lesson_id')
        quiz = get_object_or_404(Quiz, pk=quiz_id)

        # Kiểm tra đã có submission chưa
        existing_submission = QuizSubmission.objects.filter(
            quiz=quiz,
            user=request.user,
            status=QuizSubmission.STATUS_IN_PROGRESS
        ).first()

        if existing_submission:
            return Response(
                {"message": "You already have an active submission for this quiz"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Tạo snapshot của quiz hiện tại
        quiz_snapshot = {
            "snapshot_version": "1.0",
            "snapshot_created_at": timezone.now().isoformat(),
            "quiz_id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "time_limit_seconds": quiz.time_limit_seconds,
            "questions": []
        }

        for question in quiz.questions.all().order_by('sequence'):
            question_data = {
                "question_id": question.id,
                "content": question.content,
                "question_type": question.question_type,
                "points": question.points,
                "sequence": question.sequence,
                "options": []
            }

            for option in question.options.all():
                question_data["options"].append({
                    "option_id": option.id,
                    "option_text": option.option_text,
                    "is_correct": option.is_correct
                })

            quiz_snapshot["questions"].append(question_data)

        # Tạo submission
        submission_data = {
            'quiz': quiz,
            'user': request.user,
            'status': QuizSubmission.STATUS_IN_PROGRESS,
            'quiz_snapshot': quiz_snapshot
        }
        
        # Thêm lesson nếu có
        if lesson_id:
            from course.models import Lesson
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            submission_data['lesson'] = lesson
        
        submission = QuizSubmission.objects.create(**submission_data)

        serializer = QuizSubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizSubmissionAnswerView(APIView):
    """
    POST: Submit câu trả lời cho 1 question trong submission
    """
    authentication_classes = [CustomJWTAuthentication]

    def post(self, request, submission_id):
        submission = get_object_or_404(
            QuizSubmission,
            pk=submission_id,
            user=request.user
        )

        if submission.status != QuizSubmission.STATUS_IN_PROGRESS:
            return Response(
                {"message": "Submission is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = QuizAnswerSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question_id = serializer.validated_data['question_id']
        selected_option_ids = serializer.validated_data.get('selected_option_ids', [])
        text_answer = serializer.validated_data.get('text_answer', '')

        # Kiểm tra question_id có trong snapshot không
        snapshot_questions = submission.quiz_snapshot.get('questions', [])
        question_exists_in_snapshot = any(
            q['question_id'] == question_id for q in snapshot_questions
        )
        
        if not question_exists_in_snapshot:
            return Response(
                {"message": "Question not found in this submission's quiz snapshot"},
                status=status.HTTP_400_BAD_REQUEST
            )

        question = get_object_or_404(QuizQuestion, pk=question_id, quiz=submission.quiz)

        # Xóa câu trả lời cũ nếu có
        QuizAnswer.objects.filter(
            submission=submission,
            question=question
        ).delete()

        # Tạo câu trả lời mới
        if selected_option_ids:
            for option_id in selected_option_ids:
                option = get_object_or_404(QuizOption, pk=option_id, question=question)
                QuizAnswer.objects.create(
                    submission=submission,
                    question=question,
                    selected_option=option,
                    text_answer=text_answer
                )
        else:
            QuizAnswer.objects.create(
                submission=submission,
                question=question,
                text_answer=text_answer
            )

        return Response(
            {"message": "Answer saved successfully"},
            status=status.HTTP_200_OK
        )


class QuizSubmissionSubmitView(APIView):
    """
    POST: Submit (hoàn thành) bài quiz và tính điểm
    """
    authentication_classes = [CustomJWTAuthentication]

    def post(self, request, submission_id):
        submission = get_object_or_404(
            QuizSubmission,
            pk=submission_id,
            user=request.user
        )

        if submission.status != QuizSubmission.STATUS_IN_PROGRESS:
            return Response(
                {"message": "Submission is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kiểm tra snapshot có tồn tại không
        if not submission.quiz_snapshot or not submission.quiz_snapshot.get('questions'):
            return Response(
                {"message": "Invalid quiz snapshot"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Tính điểm
        total_score = 0.0
        snapshot_questions = submission.quiz_snapshot.get('questions', [])

        for snapshot_q in snapshot_questions:
            question_id = snapshot_q['question_id']
            question_type = snapshot_q['question_type']
            points = snapshot_q['points']

            # Lấy đáp án đúng từ snapshot
            correct_option_ids = set(
                opt['option_id'] for opt in snapshot_q['options']
                if opt['is_correct']
            )

            # Lấy đáp án user đã chọn
            user_answers = QuizAnswer.objects.filter(
                submission=submission,
                question_id=question_id
            )

            selected_option_ids = set(
                answer.selected_option.id
                for answer in user_answers
                if answer.selected_option
            )

            # Chấm điểm
            if question_type == QuizQuestion.QUESTION_TYPE_SINGLE:
                # Single choice: đúng hoàn toàn mới được điểm
                if selected_option_ids == correct_option_ids:
                    points_awarded = points
                else:
                    points_awarded = 0.0
            else:
                # Multiple choice: tính % đúng
                if not correct_option_ids:
                    points_awarded = 0.0
                else:
                    correct_selected = len(selected_option_ids & correct_option_ids)
                    incorrect_selected = len(selected_option_ids - correct_option_ids)
                    total_correct = len(correct_option_ids)

                    if incorrect_selected > 0:
                        points_awarded = 0.0
                    else:
                        points_awarded = points * (correct_selected / total_correct)

            # Cập nhật points_awarded cho answers
            user_answers.update(points_awarded=points_awarded)
            total_score += points_awarded

        # Cập nhật submission
        submission.total_score = total_score
        submission.status = QuizSubmission.STATUS_SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save()

        serializer = QuizSubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuizSubmissionListView(APIView):
    """
    GET: Lấy danh sách submissions của user
    """
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request):
        submissions = QuizSubmission.objects.filter(
            user=request.user
        ).order_by('-started_at')

        serializer = QuizSubmissionSerializer(submissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuizSubmissionDetailView(APIView):
    """
    GET: Xem chi tiết submission (bao gồm snapshot và answers)
    """
    authentication_classes = [CustomJWTAuthentication]

    def get(self, request, submission_id):
        submission = get_object_or_404(
            QuizSubmission,
            pk=submission_id,
            user=request.user
        )

        serializer = QuizSubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_200_OK)

