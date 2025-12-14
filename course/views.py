from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.shortcuts import redirect
from django.http import HttpResponse
import uuid

from common.authentication import CustomJWTAuthentication
from .models import Language, Course, Lesson, LessonResource, Tag, File, Order, Enrollment
from .models import Language, Course, Lesson, LessonResource, Tag, File, LessonQuiz
from .serializers import (
    LanguageSerializer, CourseSerializer, LessonSerializer, 
    LessonResourceSerializer, TagSerializer, FileSerializer, OrderSerializer, EnrollmentSerializer
)
from .vnpay_service import VNPayService


class LanguageView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow any user to view languages list"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    # Lấy danh sách hoặc tạo mới
    def get(self, request):
        languages = Language.objects.all().order_by("name")
        serializer = LanguageSerializer(languages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LanguageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LanguageDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Language.objects.get(pk=pk)
        except Language.DoesNotExist:
            return None

    # Lấy chi tiết
    def get(self, request, pk):
        language = self.get_object(pk)
        if not language:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LanguageSerializer(language)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Cập nhật
    def put(self, request, pk):
        language = self.get_object(pk)
        if not language:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LanguageSerializer(language, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Cập nhật một phần (PATCH)
    def patch(self, request, pk):
        language = self.get_object(pk)
        if not language:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LanguageSerializer(language, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Xóa
    def delete(self, request, pk):
        language = self.get_object(pk)
        if not language:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        language.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Course Views
class CourseView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow any user to view courses list"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        """Lấy danh sách courses với filter và search"""
        courses = Course.objects.prefetch_related('languages', 'tags', 'lessons', 'enrollments')
        
        # Filter by slug
        slug = request.query_params.get('slug')
        if slug:
            courses = courses.filter(slug=slug)
        
        # Filter by published status
        is_published = request.query_params.get('is_published')
        if is_published is not None:
            courses = courses.filter(is_published=is_published.lower() == 'true')
        
        # Filter by level
        level = request.query_params.get('level')
        if level:
            courses = courses.filter(level=level)
        
        # Filter by language
        language_id = request.query_params.get('language_id')
        if language_id:
            courses = courses.filter(languages__id=language_id)
        
        # Filter by tag
        tag_id = request.query_params.get('tag_id')
        if tag_id:
            courses = courses.filter(tags__id=tag_id)
        
        # Search by title or description
        search = request.query_params.get('search')
        if search:
            courses = courses.filter(
                Q(title__icontains=search) | 
                Q(short_description__icontains=search) |
                Q(long_description__icontains=search)
            )
        
        # Order by
        ordering = request.query_params.get('ordering', '-created_at')
        courses = courses.distinct().order_by(ordering)
        
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Tạo course mới"""
        # Handle banner file upload
        banner_file = request.FILES.get('banner_file')
        data = request.data.copy()
        
        if banner_file:
            # Create File instance for banner
            file_instance = File.objects.create(
                storage_key=banner_file,
                filename=banner_file.name,
                file_type=banner_file.content_type,
                size=banner_file.size,
                is_public=True
            )
            data['banner'] = file_instance.id
        
        serializer = CourseSerializer(data=data)
        if serializer.is_valid():
            # Set created_by to current user
            serializer.save(created_by=request.user, updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk=None, slug=None):
        try:
            if slug:
                return Course.objects.get(slug=slug)
            elif pk:
                return Course.objects.get(pk=pk)
            return None
        except Course.DoesNotExist:
            return None

    def get(self, request, pk=None, slug=None):
        """Lấy chi tiết course theo ID hoặc slug"""
        try:
            if slug:
                course = Course.objects.prefetch_related(
                    'languages', 'tags', 'lessons', 'enrollments'
                ).get(slug=slug)
            elif pk:
                course = Course.objects.prefetch_related(
                    'languages', 'tags', 'lessons', 'enrollments'
                ).get(pk=pk)
            else:
                return Response({"detail": "ID or slug required"}, status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk=None, slug=None):
        """Cập nhật course"""
        course = self.get_object(pk=pk, slug=slug)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle banner file upload
        banner_file = request.FILES.get('banner_file')
        data = request.data.copy()
        
        if banner_file:
            # Create File instance for banner
            file_instance = File.objects.create(
                storage_key=banner_file,
                filename=banner_file.name,
                file_type=banner_file.content_type,
                size=banner_file.size,
                is_public=True
            )
            data['banner'] = file_instance.id
        
        serializer = CourseSerializer(course, data=data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None, slug=None):
        """Cập nhật một phần course"""
        course = self.get_object(pk=pk, slug=slug)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle banner file upload
        banner_file = request.FILES.get('banner_file')
        data = request.data.copy()
        
        if banner_file:
            # Create File instance for banner
            file_instance = File.objects.create(
                storage_key=banner_file,
                filename=banner_file.name,
                file_type=banner_file.content_type,
                size=banner_file.size,
                is_public=True
            )
            data['banner'] = file_instance.id
        
        serializer = CourseSerializer(course, data=data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Xóa course"""
        course = self.get_object(pk)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Lesson Views
class LessonView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lấy danh sách lessons"""
        lessons = Lesson.objects.select_related('course').prefetch_related('resources', 'lesson_quizzes__quiz')
        
        # Filter by course (support both course_id and course)
        course_id = request.query_params.get('course_id') or request.query_params.get('course')
        if course_id:
            lessons = lessons.filter(course_id=course_id)
        
        # Search by title or description
        search = request.query_params.get('search')
        if search:
            lessons = lessons.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Order by sequence
        lessons = lessons.order_by('sequence', 'created_at')
        
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Tạo lesson mới"""
        serializer = LessonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Lesson.objects.get(pk=pk)
        except Lesson.DoesNotExist:
            return None

    def get(self, request, pk):
        """Lấy chi tiết lesson"""
        try:
            lesson = Lesson.objects.select_related('course').prefetch_related('resources__file', 'lesson_quizzes__quiz').get(pk=pk)
        except Lesson.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LessonSerializer(lesson)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Cập nhật lesson"""
        lesson = self.get_object(pk)
        if not lesson:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonSerializer(lesson, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Cập nhật một phần lesson"""
        lesson = self.get_object(pk)
        if not lesson:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Xóa lesson"""
        lesson = self.get_object(pk)
        if not lesson:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Lesson Resource Views
class LessonResourceView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lấy danh sách lesson resources"""
        resources = LessonResource.objects.all()
        
        # Filter by lesson
        lesson_id = request.query_params.get('lesson_id')
        if lesson_id:
            resources = resources.filter(lesson_id=lesson_id)
        
        # Filter by type
        resource_type = request.query_params.get('type')
        if resource_type:
            resources = resources.filter(type=resource_type)
        
        # Order by sequence
        resources = resources.order_by('sequence', 'created_at')
        
        serializer = LessonResourceSerializer(resources, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Tạo lesson resource mới"""
        # Debug logging
        print("=== LessonResource POST Debug ===")
        print(f"request.data: {request.data}")
        print(f"request.FILES: {request.FILES}")
        print(f"request.POST: {request.POST}")
        print(f"Content-Type: {request.content_type}")
        
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            print(f"File found: {uploaded_file.name}")
            file_instance = File.objects.create(
                storage_key=uploaded_file,
                filename=uploaded_file.name,
                file_type=uploaded_file.content_type,
                size=uploaded_file.size,
                is_public=True
            )
            print(f"File instance created with ID: {file_instance.id}")
            
            # Tạo dict mới thay vì copy request.data (vì không thể copy file object)
            data = {
                'lesson': request.data.get('lesson'),
                'type': request.data.get('type'),
                'title': request.data.get('title', ''),
                'sequence': request.data.get('sequence', 0),
                'file': file_instance.id
            }
        else:
            print("No file found in request")
            data = {
                'lesson': request.data.get('lesson'),
                'type': request.data.get('type'),
                'title': request.data.get('title', ''),
                'content': request.data.get('content', ''),
                'url': request.data.get('url', ''),
                'sequence': request.data.get('sequence', 0)
            }

        serializer = LessonResourceSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            resource = serializer.save()
            print(f"LessonResource created with ID: {resource.id}, File ID: {resource.file_id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonResourceDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return LessonResource.objects.get(pk=pk)
        except LessonResource.DoesNotExist:
            return None

    def get(self, request, pk):
        """Lấy chi tiết lesson resource"""
        resource = self.get_object(pk)
        if not resource:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonResourceSerializer(resource)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Cập nhật lesson resource"""
        resource = self.get_object(pk)
        if not resource:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Debug logging
        print("=== LessonResource PUT Debug ===")
        print(f"Resource ID: {pk}")
        print(f"request.FILES: {request.FILES}")
        
        # Xử lý file upload nếu có
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            print(f"New file found: {uploaded_file.name}")
            # Xóa file cũ nếu có
            if resource.file:
                old_file = resource.file
                resource.file = None
                resource.save()
                old_file.delete()
            
            # Tạo file mới
            file_instance = File.objects.create(
                storage_key=uploaded_file,
                filename=uploaded_file.name,
                file_type=uploaded_file.content_type,
                size=uploaded_file.size,
                is_public=True
            )
            print(f"New file instance created with ID: {file_instance.id}")
            
            # Tạo dict mới thay vì copy request.data (vì không thể copy file object)
            data = {
                'lesson': request.data.get('lesson'),
                'type': request.data.get('type'),
                'title': request.data.get('title', ''),
                'sequence': request.data.get('sequence', 0),
                'file': file_instance.id
            }
        else:
            print("No new file in request")
            data = {
                'lesson': request.data.get('lesson'),
                'type': request.data.get('type'),
                'title': request.data.get('title', ''),
                'content': request.data.get('content', ''),
                'url': request.data.get('url', ''),
                'sequence': request.data.get('sequence', 0)
            }
        
        serializer = LessonResourceSerializer(resource, data=data)
        if serializer.is_valid():
            serializer.save()
            print(f"Resource updated successfully")
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Cập nhật một phần lesson resource"""
        resource = self.get_object(pk)
        if not resource:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonResourceSerializer(resource, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Xóa lesson resource"""
        resource = self.get_object(pk)
        if not resource:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Tag Views
class TagView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Allow any user to view tags list"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        """Lấy danh sách tags"""
        tags = Tag.objects.all().order_by('name')
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Tạo tag mới"""
        serializer = TagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return None

    def get(self, request, pk):
        """Lấy chi tiết tag"""
        tag = self.get_object(pk)
        if not tag:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TagSerializer(tag)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Cập nhật tag"""
        tag = self.get_object(pk)
        if not tag:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TagSerializer(tag, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Xóa tag"""
        tag = self.get_object(pk)
        if not tag:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ===== Payment Views =====

class CreatePaymentView(APIView):
    """Tạo URL thanh toán VNPay cho khóa học"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Tạo đơn hàng và URL thanh toán VNPay
        Body: {
            "course_id": int,
            "return_url": string (optional) - URL frontend để redirect sau khi thanh toán
        }
        """
        course_id = request.data.get('course_id')
        frontend_return_url = request.data.get('return_url', '')
        
        if not course_id:
            return Response(
                {"error": "course_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found or not published"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Kiểm tra user đã đăng ký chưa
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"error": "You have already enrolled in this course"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Kiểm tra khóa học miễn phí
        if course.price <= 0:
            # Tạo enrollment trực tiếp cho khóa học miễn phí
            enrollment = Enrollment.objects.create(
                user=request.user,
                course=course
            )
            return Response({
                "message": "Successfully enrolled in free course",
                "enrollment_id": enrollment.id,
                "is_free": True
            }, status=status.HTTP_201_CREATED)
        
        # Tạo mã đơn hàng unique
        order_code = f"ORDER{uuid.uuid4().hex[:12].upper()}"
        
        # Tạo order
        order = Order.objects.create(
            user=request.user,
            course=course,
            order_code=order_code,
            amount=course.price,
            status='pending',
            metadata={
                'frontend_return_url': frontend_return_url
            }
        )
        
        # Tạo URL thanh toán VNPay
        vnpay_service = VNPayService()
        
        # Lấy IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_addr = x_forwarded_for.split(',')[0]
        else:
            ip_addr = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Tạo mô tả đơn hàng - Loại bỏ ký tự đặc biệt cho VNPay
        # VNPay chỉ chấp nhận: a-z, A-Z, 0-9, space
        import re
        safe_course_title = re.sub(r'[^a-zA-Z0-9 ]', '', course.title)
        # Thay space bằng underscore hoặc hyphen để tránh lỗi encoding
        safe_course_title = safe_course_title.replace(' ', '_')
        order_desc = f"Thanh_toan_khoa_hoc_{safe_course_title}"
        # Giới hạn độ dài (VNPay max 255 chars)
        order_desc = order_desc[:255]
        
        payment_url = vnpay_service.create_payment_url(
            order_code=order_code,
            amount=float(order.amount),
            order_desc=order_desc,
            ip_addr=ip_addr,
            locale='vn'
        )
        
        return Response({
            "order_id": order.id,
            "order_code": order.order_code,
            "amount": order.amount,
            "payment_url": payment_url,
            "course": {
                "id": course.id,
                "title": course.title,
                "slug": course.slug
            }
        }, status=status.HTTP_201_CREATED)


class VNPayReturnView(APIView):
    """Xử lý callback từ VNPay sau khi thanh toán"""
    authentication_classes = []  # Không cần authentication vì đây là callback từ VNPay
    permission_classes = []

    def get(self, request):
        """
        VNPay sẽ redirect về URL này với các tham số:
        - vnp_TxnRef: Mã đơn hàng
        - vnp_ResponseCode: Mã phản hồi (00 = thành công)
        - vnp_TransactionNo: Mã giao dịch tại VNPay
        - vnp_SecureHash: Chữ ký để xác thực
        - ...
        """
        query_params = request.query_params.dict()
        
        vnpay_service = VNPayService()
        
        # Xác thực response từ VNPay
        is_valid, response_code, txn_ref = vnpay_service.validate_response(query_params)
        
        if not is_valid:
            return Response(
                {"error": "Invalid signature from VNPay"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lấy order
        try:
            order = Order.objects.get(order_code=txn_ref)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cập nhật thông tin order
        order.vnp_txn_ref = query_params.get('vnp_TxnRef', '')
        order.vnp_transaction_no = query_params.get('vnp_TransactionNo', '')
        order.vnp_response_code = response_code
        order.vnp_bank_code = query_params.get('vnp_BankCode', '')
        order.vnp_pay_date = query_params.get('vnp_PayDate', '')
        
        # Kiểm tra thanh toán thành công
        if vnpay_service.is_success_response(response_code):
            with transaction.atomic():
                # Cập nhật order status
                order.status = 'completed'
                order.completed_at = timezone.now()
                order.save()
                
                # Tạo enrollment
                enrollment, created = Enrollment.objects.get_or_create(
                    user=order.user,
                    course=order.course
                )
        else:
            order.status = 'failed'
            order.save()
        
        # Redirect về frontend
        frontend_return_url = order.metadata.get('frontend_return_url', '') if order.metadata else ''
        
        if frontend_return_url:
            # Thêm params vào URL frontend
            separator = '&' if '?' in frontend_return_url else '?'
            redirect_url = f"{frontend_return_url}{separator}order_code={order.order_code}&status={order.status}"
            return redirect(redirect_url)
        
        # Nếu không có frontend URL, trả về JSON
        return Response({
            "order_code": order.order_code,
            "status": order.status,
            "response_code": response_code,
            "message": "Payment successful" if order.status == 'completed' else "Payment failed"
        })


class CheckPaymentStatusView(APIView):
    """Kiểm tra trạng thái thanh toán"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_code):
        """
        Kiểm tra trạng thái đơn hàng
        URL: /api/payment/status/<order_code>/
        """
        try:
            order = Order.objects.get(order_code=order_code, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderHistoryView(APIView):
    """Lấy lịch sử đơn hàng của user"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lấy danh sách orders của user hiện tại"""
        orders = Order.objects.filter(user=request.user).select_related('course')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CheckEnrollmentView(APIView):
    """Kiểm tra xem user đã đăng ký khóa học chưa"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """
        Kiểm tra enrollment
        URL: /api/enrollment/check/<course_id>/
        """
        is_enrolled = Enrollment.objects.filter(
            user=request.user,
            course_id=course_id
        ).exists()
        
        return Response({
            "is_enrolled": is_enrolled,
            "course_id": course_id
        }, status=status.HTTP_200_OK)


class EnrollmentListView(APIView):
    """Quản lý enrollments"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Lấy danh sách khóa học đã đăng ký của user"""
        enrollments = Enrollment.objects.filter(user=request.user).select_related('course')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

