from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from common.authentication import CustomJWTAuthentication
from .models import Language, Course, Lesson, LessonResource, Tag, File
from .serializers import (
    LanguageSerializer, CourseSerializer, LessonSerializer, 
    LessonResourceSerializer, TagSerializer, FileSerializer
)


class LanguageView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

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

    def get(self, request):
        """Lấy danh sách courses với filter và search"""
        courses = Course.objects.all()
        
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
        courses = courses.order_by(ordering)
        
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Tạo course mới"""
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            # Set created_by to current user
            serializer.save(created_by=request.user, updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return None

    def get(self, request, pk):
        """Lấy chi tiết course"""
        course = self.get_object(pk)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Cập nhật course"""
        course = self.get_object(pk)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Cập nhật một phần course"""
        course = self.get_object(pk)
        if not course:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course, data=request.data, partial=True)
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
        lessons = Lesson.objects.all()
        
        # Filter by course
        course_id = request.query_params.get('course_id')
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
        lesson = self.get_object(pk)
        if not lesson:
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
        serializer = LessonResourceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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
        serializer = LessonResourceSerializer(resource, data=request.data)
        if serializer.is_valid():
            serializer.save()
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
