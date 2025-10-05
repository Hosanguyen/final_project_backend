from django.urls import path

from .views import (
    RegisterView, 
    LoginView, 
    RefreshTokenView, 
    LogoutView, 
    HelloAPIView, 
    AdminCRUDUser, 
    UserProfileView, 
    UserResetPasswordView, 
    UserAvatarView)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="login"),
    path('hello/', HelloAPIView.as_view(), name='hello'),
    path('admin/create/', AdminCRUDUser.as_view(), name='admin_create_user'),
    path('admin/update/<int:id>/', AdminCRUDUser.as_view(), name='admin_update_user'),
    path('admin/delete/<int:id>/', AdminCRUDUser.as_view(), name='admin_delete_user'),
    path('admin/list/', AdminCRUDUser.as_view(), name='admin_list_user'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', UserProfileView.as_view(), name='user_profile_update'),
    path('profile/reset-password/', UserResetPasswordView.as_view(), name='user_reset_password'),
    path('profile/avatar/', UserAvatarView.as_view(), name='user_avatar'),
    path('profile/avatar/delete/', UserAvatarView.as_view(), name='user_avatar_delete'),
]
