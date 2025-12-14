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
    UserAssignRolesView,
    UserRemoveRolesView,
    # Rating views
    GlobalRankingView,
    UserRatingDetailView,
    UserRatingHistoryView,
    UpdateContestRatingsView,
)

# User Reports Views
from .user_reports_views import (
    UserReportsStatsView,
    UserReportsGrowthChartView,
    UserReportsLevelDistributionView,
    UserReportsCourseEnrollmentsView,
    UserReportsContestStatsView,
    UserReportsTopUsersView,
    UserReportsAllUsersView,
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
    path('admin/detail/<int:id>/', AdminCRUDUser.as_view(), name='admin_detail_user'),
    path('admin/<int:user_id>/assign-roles/', UserAssignRolesView.as_view(), name='user-assign-roles'),
    path('admin/<int:user_id>/remove-roles/', UserRemoveRolesView.as_view(), name='user-remove-roles'),
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

    # ============= GLOBAL RANKING ENDPOINTS =============
    # Global leaderboard
    path('ranking/global/', GlobalRankingView.as_view(), name='global-ranking'),
    
    # User rating info
    path('rating/me/', UserRatingDetailView.as_view(), name='my-rating'),
    path('rating/<int:user_id>/', UserRatingDetailView.as_view(), name='user-rating'),
    
    # User rating history
    path('rating/history/me/', UserRatingHistoryView.as_view(), name='my-rating-history'),
    path('rating/history/<int:user_id>/', UserRatingHistoryView.as_view(), name='user-rating-history'),
    
    # Admin: update contest ratings
    path('rating/contest/<int:contest_id>/update/', UpdateContestRatingsView.as_view(), name='update-contest-ratings'),

    # ============= USER REPORTS ENDPOINTS (ADMIN) =============
    # Statistics overview
    path('reports/stats/', UserReportsStatsView.as_view(), name='user-reports-stats'),
    
    # Growth chart data
    path('reports/growth-chart/', UserReportsGrowthChartView.as_view(), name='user-reports-growth-chart'),
    
    # Level distribution
    path('reports/level-distribution/', UserReportsLevelDistributionView.as_view(), name='user-reports-level-distribution'),
    
    # Course enrollments
    path('reports/course-enrollments/', UserReportsCourseEnrollmentsView.as_view(), name='user-reports-course-enrollments'),
    
    # Contest statistics
    path('reports/contest-stats/', UserReportsContestStatsView.as_view(), name='user-reports-contest-stats'),
    
    # Top users
    path('reports/top-users/', UserReportsTopUsersView.as_view(), name='user-reports-top-users'),
    
    # All users list with pagination
    path('reports/all-users/', UserReportsAllUsersView.as_view(), name='user-reports-all-users'),

]
