from django.urls import path
from .views import LanguageView, LanguageDetailView

urlpatterns = [
    path("languages/", LanguageView.as_view(), name="language-list-create"),
    path("languages/<int:pk>/", LanguageDetailView.as_view(), name="language-detail"),
]
