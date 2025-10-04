from django.urls import path
from .views import RegisterView, LoginView, HelloAPIView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path('hello/', HelloAPIView.as_view(), name='hello'),
    
]
