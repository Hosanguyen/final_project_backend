from django.urls import path
from . import views

urlpatterns = [
    # Quiz CRUD
    path('', views.QuizListView.as_view(), name='quiz-list'),
    path('<int:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    
    # Quiz Submissions
    path('submissions/', views.QuizSubmissionListView.as_view(), name='quiz-submission-list'),
    path('submissions/start/', views.QuizSubmissionStartView.as_view(), name='quiz-submission-start'),
    path('submissions/<int:submission_id>/', views.QuizSubmissionDetailView.as_view(), name='quiz-submission-detail'),
    path('submissions/<int:submission_id>/answer/', views.QuizSubmissionAnswerView.as_view(), name='quiz-submission-answer'),
    path('submissions/<int:submission_id>/submit/', views.QuizSubmissionSubmitView.as_view(), name='quiz-submission-submit'),
]
