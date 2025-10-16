from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from common.authentication import CustomJWTAuthentication
from .models import Language
from .serializers import LanguageSerializer


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
