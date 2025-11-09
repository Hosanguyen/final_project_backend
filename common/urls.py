from django.urls import path
from .media_views import media_proxy

urlpatterns = [
    path('media-proxy/', media_proxy, name='media-proxy'),
]
