from django.urls import path
from .views import LoginAPIView, HelloAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name="login"),
    path('hello/', HelloAPIView.as_view(), name='hello'),
]
