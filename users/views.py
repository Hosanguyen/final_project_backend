from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.apps import apps
from datetime import datetime

from .models import User, RevokedToken, Role, Permission, PermissionCategory
from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserListSerializer, 
    AdminUpdateUserSerializer, 
    UserProfileSerializer, 
    UserResetPasswordSerializer, 
    AvatarSerializer,
    PermissionCategorySerializer,
    PermissionCategoryListSerializer,
    PermissionSerializer,
    PermissionListSerializer,
    RoleSerializer,
    RoleListSerializer,
    RoleCreateUpdateSerializer,
    AssignPermissionsToRoleSerializer,
    RemovePermissionsFromRoleSerializer,
    UserWithRolesSerializer,
    AssignRolesToUserSerializer,
    RemoveRolesFromUserSerializer,
    # Rating serializers
    UserRatingSerializer,
    ContestRatingChangeSerializer,
    GlobalRankingSerializer,
)
from common.authentication import CustomJWTAuthentication

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({"user": serializer.data, "tokens": tokens}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.active:
            return Response({"detail": "User is not active"}, status=status.HTTP_401_UNAUTHORIZED)
        # cập nhật last_login
        user.last_login_at = timezone.now()
        user.last_login_ip = request.META.get("REMOTE_ADDR")
        user.save(update_fields=["last_login_at", "last_login_ip"])
        user_data = UserProfileSerializer(user).data
        tokens = get_tokens_for_user(user)
        return Response({
            "tokens": tokens,
            "user": user_data})


class HelloAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]  
    permission_classes = [IsAuthenticated]  # bắt buộc phải có token

    def get(self, request):
        if request.user.has_perm('admin', 'users.read'):
            print("User has users.read permission")
        return Response({
            "message": f"Hello, {request.user.username}! Token của bạn hợp lệ."
        })

class RefreshTokenView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            
            jti = refresh.get('jti')

            if RevokedToken.objects.filter(jti=jti).exists():
                return Response(
                    {"detail": "This refresh token has been revoked"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            exp = refresh.get('exp')
            user_id = refresh.get('user_id')
            RevokedToken.objects.create(
                jti=jti,
                user_id=user_id,
                expires_at=datetime.fromtimestamp(exp)
            )
            user = User.objects.get(id=user_id)
            tokens = get_tokens_for_user(user)
            
            return Response({
                "tokens": tokens
            }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response(
                {"detail": "Token is invalid or expired"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            jti = refresh.get('jti')
            user_id = refresh.get('user_id')
            exp = refresh.get('exp')
            
            RevokedToken.objects.get_or_create(
                jti=jti,
                defaults={
                    'user_id': user_id,
                    'expires_at': datetime.fromtimestamp(exp)
                }
            )
            
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class AdminCRUDUser(APIView):
    authentication_classes = [CustomJWTAuthentication]  
    # permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({"user": serializer.data, "tokens": tokens}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request, id=None):
        # Nếu có id thì trả về chi tiết user
        if id:
            user = get_object_or_404(User, id=id)
            serializer = UserWithRolesSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Nếu không có id thì trả về danh sách
        users = User.objects.all()
        serializer = UserWithRolesSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, id):
        user = get_object_or_404(User, id=id)
        serializer = AdminUpdateUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "User updated successfully.", "user": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        user = get_object_or_404(User, id=id)
        username = user.username 
        user.delete()
        return Response(
            {"detail": f"User '{username}' deleted successfully."},
            status=status.HTTP_200_OK
        )
    
class UserAssignRolesView(APIView):
    """
    POST: GÁN roles cho user (THAY THẾ toàn bộ roles cũ)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """
        Request body:
        {
            "role_ids": [1, 2, 3]
        }
        """
        user = get_object_or_404(User, id=user_id)
        serializer = AssignRolesToUserSerializer(data=request.data)
        
        if serializer.is_valid():
            role_ids = serializer.validated_data["role_ids"]
            roles = Role.objects.filter(id__in=role_ids)
            
            # THAY THẾ toàn bộ roles (xóa cũ, gán mới)
            user.roles.set(roles)
            
            # Trả về user với roles đầy đủ
            response_serializer = UserWithRolesSerializer(user)
            return Response(
                {
                    "detail": f"Assigned {len(roles)} role(s) to user '{user.username}'",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRemoveRolesView(APIView):
    """
    POST: XÓA roles khỏi user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """
        Request body:
        {
            "role_ids": [1, 2]
        }
        """
        user = get_object_or_404(User, id=user_id)
        serializer = RemoveRolesFromUserSerializer(data=request.data)
        
        if serializer.is_valid():
            role_ids = serializer.validated_data["role_ids"]
            roles = Role.objects.filter(id__in=role_ids)
            
            # XÓA roles
            user.roles.remove(*roles)
            
            # Trả về user với roles đầy đủ
            response_serializer = UserWithRolesSerializer(user)
            return Response(
                {
                    "detail": f"Removed {len(roles)} role(s) from user '{user.username}'",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if request.data.get("is_delete_avatar", False):
                if user.avatar_url:
                    try:
                        user.avatar_url.delete(save=False)
                    except Exception as e:
                        print(f"Error deleting avatar: {e}")
                    user.avatar_url = None
                    user.save(update_fields=["avatar_url"])
            serializer.save()
            return Response({"detail": "User updated successfully.", "user": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserResetPasswordView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        serializer = UserResetPasswordSerializer(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

class UserAvatarView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        user = request.user
        if not user.avatar_url:
            return Response(
                {"detail": "User has no avatar to delete."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user.avatar_url.delete(save=False)
        except Exception as e:
            print(f"Error deleting avatar: {e}")
        user.avatar_url = None
        user.save(update_fields=["avatar_url"])
        return Response({"detail": "Avatar deleted successfully."}, status=status.HTTP_200_OK)



# PERMISSION CATEGORY CRUD

class PermissionCategoryListCreateView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = PermissionCategory.objects.all().order_by('name')
        serializer = PermissionCategoryListSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PermissionCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Permission category created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PermissionCategoryDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        category = get_object_or_404(PermissionCategory, id=id)
        serializer = PermissionCategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        category = get_object_or_404(PermissionCategory, id=id)
        serializer = PermissionCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Permission category updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        category = get_object_or_404(PermissionCategory, id=id)
        category_name = category.name
        category.delete()
        return Response(
            {"detail": f"Permission category '{category_name}' deleted successfully"},
            status=status.HTTP_200_OK
        )


# PERMISSION CRUD

class PermissionListCreateView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permissions = Permission.objects.all().select_related('category').order_by('code')
        serializer = PermissionListSerializer(permissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Permission created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PermissionDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        permission = get_object_or_404(Permission.objects.select_related('category'), id=id)
        serializer = PermissionSerializer(permission)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        permission = get_object_or_404(Permission, id=id)
        serializer = PermissionSerializer(permission, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Permission updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        permission = get_object_or_404(Permission, id=id)
        permission_code = permission.code
        permission.delete()
        return Response(
            {"detail": f"Permission '{permission_code}' deleted successfully"},
            status=status.HTTP_200_OK
        )


# ROLE CRUD (với quản lý permissions)

class RoleListCreateView(APIView):
    """
    GET: Lấy danh sách tất cả Role (không có permissions chi tiết)
    POST: Tạo Role mới VÀ gán permissions luôn
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = Role.objects.all().order_by('name')
        serializer = RoleListSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RoleCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            
            response_serializer = RoleSerializer(role)
            return Response(
                {
                    "detail": "Role created successfully",
                    "data": response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        role = get_object_or_404(
            Role.objects.prefetch_related('permissions__category'), 
            id=id
        )
        serializer = RoleSerializer(role)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        role = get_object_or_404(Role, id=id)
        serializer = RoleCreateUpdateSerializer(role, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_role = serializer.save()
            
            response_serializer = RoleSerializer(updated_role)
            return Response(
                {
                    "detail": "Role updated successfully",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        role = get_object_or_404(Role, id=id)
        role_name = role.name
        
        user_count = role.users.count()
        if user_count > 0:
            return Response(
                {
                    "detail": f"Cannot delete role '{role_name}'. It is assigned to {user_count} user(s)."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role.delete()
        return Response(
            {"detail": f"Role '{role_name}' deleted successfully"},
            status=status.HTTP_200_OK
        )


# ROLE PERMISSIONS MANAGEMENT (Thêm/Xóa permissions từ role)

class RoleAssignPermissionsView(APIView):
    """
    POST: THÊM permissions vào role (không xóa permissions cũ)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, role_id):
        """
        Request body:
        {
            "permission_ids": [7, 8, 9]
        }
        """
        role = get_object_or_404(Role, id=role_id)
        serializer = AssignPermissionsToRoleSerializer(data=request.data)
        
        if serializer.is_valid():
            permission_ids = serializer.validated_data["permission_ids"]
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # THÊM permissions (không xóa cái cũ)
            role.permissions.add(*permissions)
            
            # Trả về role với permissions đầy đủ
            response_serializer = RoleSerializer(role)
            return Response(
                {
                    "detail": f"Added {len(permissions)} permission(s) to role '{role.name}'",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoleRemovePermissionsView(APIView):
    """
    POST: XÓA permissions khỏi role
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, role_id):
        """
        Request body:
        {
            "permission_ids": [7, 8]
        }
        """
        role = get_object_or_404(Role, id=role_id)
        serializer = RemovePermissionsFromRoleSerializer(data=request.data)
        
        if serializer.is_valid():
            permission_ids = serializer.validated_data["permission_ids"]
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # XÓA permissions
            role.permissions.remove(*permissions)
            
            # Trả về role với permissions đầy đủ
            response_serializer = RoleSerializer(role)
            return Response(
                {
                    "detail": f"Removed {len(permissions)} permission(s) from role '{role.name}'",
                    "data": response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# HELPER VIEWS (Lấy danh sách để hiển thị dropdown/checkbox)

class AllPermissionsForSelectionView(APIView):
    """
    GET: Lấy tất cả permissions nhóm theo category
    Dùng cho frontend hiển thị checkbox khi tạo/sửa role
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = PermissionCategory.objects.prefetch_related('permission_set').all()
        
        result = []
        for category in categories:
            permissions = category.permission_set.all().order_by('code')
            result.append({
                "category_id": category.id,
                "category_name": category.name,
                "category_description": category.description,
                "permissions": PermissionListSerializer(permissions, many=True).data
            })
        
        return Response(result, status=status.HTTP_200_OK)


class AllRolesForSelectionView(APIView):
    """
    GET: Lấy tất cả roles (chỉ id và name)
    Dùng cho frontend hiển thị dropdown khi gán role cho user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import RoleSimpleSerializer
        roles = Role.objects.all().order_by('name')
        serializer = RoleSimpleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ============= GLOBAL RANKING VIEWS =============

class GlobalRankingView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    """
    GET: Lấy bảng xếp hạng global
    Query params:
    - page: số trang (default=1)
    - limit: số user mỗi trang (default=50, max=100)
    """
    
    def get(self, request):
        from .rating_service import RatingService
        from .models import User
        
        # Get pagination params
        page = int(request.query_params.get('page', 1))
        limit = min(int(request.query_params.get('limit', 50)), 100)  # Max 100
        offset = (page - 1) * limit
        
        # Get leaderboard
        users = RatingService.get_global_leaderboard(limit=limit, offset=offset)
        
        # Format data with ranking
        ranking_data = []
        for idx, user in enumerate(users, start=offset + 1):
            ranking_data.append({
                'rank': idx,
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name or user.username,
                'avatar_url': user.avatar_url,
                'current_rating': user.current_rating,
                'max_rating': user.max_rating,
                'rank_title': user.rank,
                'rank_color': User.get_rank_color(user.rank),
                'contests_participated': user.contests_participated,
                'contests_won': user.contests_won,
                'total_problems_solved': user.total_problems_solved,
            })
        
        serializer = GlobalRankingSerializer(ranking_data, many=True)
        
        # Get total count for pagination
        total_count = User.objects.count()
        
        return Response({
            'rankings': serializer.data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': (total_count + limit - 1) // limit
            }
        }, status=status.HTTP_200_OK)


class UserRatingDetailView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    """
    GET: Lấy thông tin rating chi tiết của user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        from .rating_service import RatingService
        
        # Nếu không có user_id, lấy user hiện tại
        target_user_id = user_id if user_id else request.user.id
        
        user_rating = RatingService.get_user_rating_info(target_user_id)
        
        if not user_rating:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserRatingSerializer(user_rating)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRatingHistoryView(APIView):
    """
    GET: Lấy lịch sử thay đổi rating của user
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        from .rating_service import RatingService
        
        # Nếu không có user_id, lấy user hiện tại
        target_user_id = user_id if user_id else request.user.id
        
        limit = min(int(request.query_params.get('limit', 50)), 100)
        
        rating_changes = RatingService.get_user_rating_history(target_user_id, limit=limit)
        serializer = ContestRatingChangeSerializer(rating_changes, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateContestRatingsView(APIView):
    """
    POST: Update rating cho tất cả participants của một contest
    Admin only - gọi sau khi contest kết thúc
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, contest_id):
        from .rating_service import RatingService
        
        # Check if user is admin
        if not request.user.is_staff:
            return Response(
                {"detail": "Only admin can update contest ratings"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        updated_count = RatingService.update_contest_ratings(contest_id)
        
        if updated_count == 0:
            return Response(
                {"detail": "No ratings updated. Contest may not be rated or has too few participants."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "detail": f"Successfully updated ratings for {updated_count} participants",
                "updated_count": updated_count
            },
            status=status.HTTP_200_OK
        )