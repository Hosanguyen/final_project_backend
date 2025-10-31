from django.urls import path
from .views import (
    ContestCreateView,
    ContestListView,
    ContestDetailView
)

urlpatterns = [
    path('', ContestListView.as_view(), name='contest-list'),
    path('create/', ContestCreateView.as_view(), name='contest-create'),
    path('<int:contest_id>/', ContestDetailView.as_view(), name='contest-detail'),
]