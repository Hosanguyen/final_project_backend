from django.urls import path
from .views import (
    ProblemListCreateView, ProblemDetailView,
    ProblemTestCasesView, TestCaseDetailView,
    ProblemStatisticsView
)

urlpatterns = [
    # Problem CRUD
    path('', ProblemListCreateView.as_view(), name='problem-list-create'),
    path('<int:id>/', ProblemDetailView.as_view(), name='problem-detail'),
    
    # Test Cases
    path('<int:problem_id>/test-cases/', ProblemTestCasesView.as_view(), name='problem-test-cases'),
    path('<int:problem_id>/test-cases/<int:testcase_id>/', TestCaseDetailView.as_view(), name='test-case-detail'),
    
    # Statistics
    path('<int:id>/statistics/', ProblemStatisticsView.as_view(), name='problem-statistics'),
]