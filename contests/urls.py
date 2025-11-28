from django.urls import path
from .views import (
    ContestCreateView,
    ContestListView,
    ContestDetailView,
    ContestProblemView,
    ContestDetailUserView,
    UserContestsView,
    UserContestDetailView,
    ContestProblemDetailView,
    ContestRegistrationView,
    ContestRegistrationStatusView,
    ContestParticipantsView,
    ContestParticipantToggleView,
    ContestLeaderboardView,
)

urlpatterns = [
    path('', ContestListView.as_view(), name='contest-list'),
    path('create/', ContestCreateView.as_view(), name='contest-create'),
    path('<int:contest_id>/', ContestDetailView.as_view(), name='contest-detail'),
    path('<int:contest_id>/problems/', ContestProblemView.as_view(), name='contest-add-problem'),
    path('<int:contest_id>/problems/<int:problem_id>/', ContestProblemView.as_view(), name='contest-remove-problem'),
    path('<int:contest_id>/leaderboard/', ContestLeaderboardView.as_view(), name='contest-leaderboard'),
    path('practice/contest/', ContestDetailUserView.as_view(), name='practice-contest-detail'),
    path('user/contests/', UserContestsView.as_view(), name='user-contests'),
    path('user/<int:contest_id>/', UserContestDetailView.as_view(), name='user-contest-detail'),
    path('contest-problem/<int:contest_problem_id>/', ContestProblemDetailView.as_view(), name='contest-problem-detail'),
    path('user/<int:contest_id>/register/', ContestRegistrationView.as_view(), name='contest-register'),
    path('user/<int:contest_id>/registration-status/', ContestRegistrationStatusView.as_view(), name='contest-registration-status'),
    path('<int:contest_id>/participants/', ContestParticipantsView.as_view(), name='contest-participants'),
    path('<int:contest_id>/participants/<int:participant_id>/toggle/', ContestParticipantToggleView.as_view(), name='contest-participant-toggle'),
]