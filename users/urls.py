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
    UserAvatarView,
    PermissionCategoryListCreateView,
    PermissionCategoryDetailView,
    PermissionListCreateView,
    PermissionDetailView,
    RoleListCreateView,
    RoleDetailView,
    RoleAssignPermissionsView,
    RoleRemovePermissionsView,
    AllPermissionsForSelectionView,
    AllRolesForSelectionView,
    ModelListView,
)


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

    # PERMISSION CATEGORY
    path('permission-categories/', PermissionCategoryListCreateView.as_view(), name='permission-categories-list-create'),
    path('permission-categories/<int:id>/', PermissionCategoryDetailView.as_view(), name='permission-categories-detail'),
    
    # PERMISSION
    path('permissions/', PermissionListCreateView.as_view(), name='permissions-list-create'),
    path('permissions/<int:id>/', PermissionDetailView.as_view(), name='permissions-detail'),
    
    # ROLE
    path('roles/', RoleListCreateView.as_view(), name='roles-list-create'),
    path('roles/<int:id>/', RoleDetailView.as_view(), name='roles-detail'),
    
    # Role Permissions Management
    path('roles/<int:role_id>/assign-permissions/', RoleAssignPermissionsView.as_view(), name='role-assign-permissions'),
    path('roles/<int:role_id>/remove-permissions/', RoleRemovePermissionsView.as_view(), name='role-remove-permissions'),
    
    # HELPER VIEWS (cho frontend)
    path('selections/permissions/', AllPermissionsForSelectionView.as_view(), name='selections-permissions'),
    path('selections/roles/', AllRolesForSelectionView.as_view(), name='selections-roles'),

    path('model/list/', ModelListView.as_view(), name="Model List")
]
