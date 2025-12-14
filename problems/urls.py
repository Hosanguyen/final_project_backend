from django.urls import path
from .views import (
    ProblemListCreateView, ProblemDetailView,
    ProblemTestCasesView, TestCaseDetailView,
    ProblemStatisticsView,
    SubmissionCreateView, SubmissionListView, SubmissionDetailView
)
from .user_profile_views import (
    UserProblemsView, UserSubmissionsView, UserRegisteredContestsView,
    UserStatisticsView
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
    
    # Submissions
    path('<int:problem_id>/submissions/', SubmissionCreateView.as_view(), name='submission-create'),
    path('<int:problem_id>/submissions/list/', SubmissionListView.as_view(), name='submission-list-by-problem'),
    path('submissions/', SubmissionListView.as_view(), name='submission-list-all'),
    path('submissions/<int:submission_id>/', SubmissionDetailView.as_view(), name='submission-detail'),
    
    # User Profile APIs
    path('user/problems/', UserProblemsView.as_view(), name='user-problems'),
    path('user/submissions/', UserSubmissionsView.as_view(), name='user-submissions'),
    path('user/contests/', UserRegisteredContestsView.as_view(), name='user-contests'),
    path('user/statistics/', UserStatisticsView.as_view(), name='user-statistics'),
]