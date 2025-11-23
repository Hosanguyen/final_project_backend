from django.urls import path
from .views import (
    ContestCreateView,
    ContestListView,
    ContestDetailView,
    ContestProblemView,
    ContestDetailUserView,
    UserContestsView,
)

urlpatterns = [
    path('', ContestListView.as_view(), name='contest-list'),
    path('create/', ContestCreateView.as_view(), name='contest-create'),
    path('<int:contest_id>/', ContestDetailView.as_view(), name='contest-detail'),
    path('<int:contest_id>/problems/', ContestProblemView.as_view(), name='contest-add-problem'),
    path('<int:contest_id>/problems/<int:problem_id>/', ContestProblemView.as_view(), name='contest-remove-problem'),
    path('practice/contest/', ContestDetailUserView.as_view(), name='practice-contest-detail'),
    path('user/contests/', UserContestsView.as_view(), name='user-contests'),
]