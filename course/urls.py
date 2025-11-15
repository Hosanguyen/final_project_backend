from django.urls import path
from .views import (
    LanguageView, LanguageDetailView,
    CourseView, CourseDetailView,
    LessonView, LessonDetailView,
    LessonResourceView, LessonResourceDetailView,
    TagView, TagDetailView
)

urlpatterns = [
    # Language URLs
    path("languages/", LanguageView.as_view(), name="language-list-create"),
    path("languages/<int:pk>/", LanguageDetailView.as_view(), name="language-detail"),
    
    # Course URLs
    path("courses/", CourseView.as_view(), name="course-list-create"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/slug/<slug:slug>/", CourseDetailView.as_view(), name="course-detail-by-slug"),
    
    # Lesson URLs
    path("lessons/", LessonView.as_view(), name="lesson-list-create"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    
    # Lesson Resource URLs
    path("lesson-resources/", LessonResourceView.as_view(), name="lesson-resource-list-create"),
    path("lesson-resources/<int:pk>/", LessonResourceDetailView.as_view(), name="lesson-resource-detail"),
    
    # Tag URLs
    path("tags/", TagView.as_view(), name="tag-list-create"),
    path("tags/<int:pk>/", TagDetailView.as_view(), name="tag-detail"),
]
