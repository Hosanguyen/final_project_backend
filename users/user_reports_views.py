"""
User Reports Views - Statistics and Analytics for Admin Dashboard
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Max, Min, Avg, Sum
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import User
from common.authentication import CustomJWTAuthentication


class UserReportsStatsView(APIView):
    """
    GET: Lấy thống kê tổng quan người dùng theo tháng
    Query params:
        - month: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Lấy tháng từ query params, mặc định là tháng hiện tại
        month_str = request.query_params.get('month')
        
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                # Tạo timezone-aware datetime
                target_date = timezone.make_aware(datetime(year, month, 1))
            except:
                return Response(
                    {"detail": "Invalid month format. Use YYYY-MM"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Tính toán ngày đầu và cuối tháng
        month_start = target_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
        
        # Tháng trước
        prev_month_start = month_start - relativedelta(months=1)
        prev_month_end = month_start - timedelta(seconds=1)
        
        # Tổng người dùng đến cuối tháng
        total_users = User.objects.filter(
            created_at__lte=month_end,
            deleted_at__isnull=True
        ).count()
        
        # Tổng người dùng tháng trước
        total_users_prev = User.objects.filter(
            created_at__lte=prev_month_end,
            deleted_at__isnull=True
        ).count()
        
        # Người dùng mới trong tháng
        new_users = User.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end,
            deleted_at__isnull=True
        ).count()
        
        # Người dùng mới tháng trước
        new_users_prev = User.objects.filter(
            created_at__gte=prev_month_start,
            created_at__lte=prev_month_end,
            deleted_at__isnull=True
        ).count()
        
        # Người dùng hoạt động (đăng nhập trong tháng)
        active_users = User.objects.filter(
            last_login_at__gte=month_start,
            last_login_at__lte=month_end,
            deleted_at__isnull=True
        ).count()
        
        # Người dùng hoạt động tháng trước
        active_users_prev = User.objects.filter(
            last_login_at__gte=prev_month_start,
            last_login_at__lte=prev_month_end,
            deleted_at__isnull=True
        ).count()
        
        # Khóa học đã bán trong tháng
        from course.models import Enrollment
        courses_sold = Enrollment.objects.filter(
            enrolled_at__gte=month_start,
            enrolled_at__lte=month_end
        ).count()
        
        # Khóa học đã bán tháng trước
        courses_sold_prev = Enrollment.objects.filter(
            enrolled_at__gte=prev_month_start,
            enrolled_at__lte=prev_month_end
        ).count()
        
        # Tính phần trăm thay đổi
        def calculate_change(current, previous):
            if previous == 0:
                return "+100.0%" if current > 0 else "0.0%"
            change = ((current - previous) / previous) * 100
            return f"{'+' if change >= 0 else ''}{change:.1f}%"
        
        return Response({
            "total_users": total_users,
            "total_change": calculate_change(total_users, total_users_prev),
            "new_users": new_users,
            "new_change": calculate_change(new_users, new_users_prev),
            "active_users": active_users,
            "active_change": calculate_change(active_users, active_users_prev),
            "courses_sold": courses_sold,
            "courses_change": calculate_change(courses_sold, courses_sold_prev)
        }, status=http_status.HTTP_200_OK)


class UserReportsGrowthChartView(APIView):
    """
    GET: Lấy dữ liệu biểu đồ tăng trưởng người dùng theo ngày trong tháng
    Query params:
        - month: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month')
        
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                # Tạo timezone-aware datetime
                target_date = timezone.make_aware(datetime(year, month, 1))
            except:
                return Response(
                    {"detail": "Invalid month format. Use YYYY-MM"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_start = target_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
        
        # Số ngày trong tháng
        days_in_month = (month_end.day)
        
        labels = []
        total_users_data = []
        active_users_data = []
        new_users_data = []
        
        for day in range(1, days_in_month + 1):
            day_date = month_start.replace(day=day)
            day_end = day_date.replace(hour=23, minute=59, second=59)
            
            # Label format: DD/MM
            labels.append(f"{day:02d}/{month:02d}")
            
            # Tổng users đến ngày này
            total_users = User.objects.filter(
                created_at__lte=day_end,
                deleted_at__isnull=True
            ).count()
            total_users_data.append(total_users)
            
            # Active users trong ngày
            active_users = User.objects.filter(
                last_login_at__date=day_date.date(),
                deleted_at__isnull=True
            ).count()
            active_users_data.append(active_users)
            
            # New users trong ngày
            new_users = User.objects.filter(
                created_at__date=day_date.date(),
                deleted_at__isnull=True
            ).count()
            new_users_data.append(new_users)
        
        return Response({
            "labels": labels,
            "total_users": total_users_data,
            "active_users": active_users_data,
            "new_users": new_users_data
        }, status=http_status.HTTP_200_OK)


class UserReportsLevelDistributionView(APIView):
    """
    GET: Lấy phân bổ cấp độ người dùng
    Query params:
        - month: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month')
        
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                # Tạo timezone-aware datetime
                target_date = timezone.make_aware(datetime(year, month, 1))
            except:
                return Response(
                    {"detail": "Invalid month format. Use YYYY-MM"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_start = target_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
        
        # Đếm số lượng user theo rank (chỉ tính users đã tạo đến cuối tháng)
        rank_counts = User.objects.filter(
            created_at__lte=month_end,
            deleted_at__isnull=True
        ).values('rank').annotate(count=Count('id'))
        
        # Map rank counts
        rank_dict = {item['rank']: item['count'] for item in rank_counts}
        
        # Lấy RANK_CHOICES từ model và tạo label map
        rank_label_map = dict(User.RANK_CHOICES)
        
        # Chỉ lấy những rank có user (count > 0)
        labels = []
        data = []
        
        for rank_code, rank_label in User.RANK_CHOICES:
            if rank_code in rank_dict and rank_dict[rank_code] > 0:
                labels.append(rank_label)
                data.append(rank_dict[rank_code])
        
        # Nếu không có data nào, trả về empty
        if not labels:
            labels = []
            data = []
        
        return Response({
            "labels": labels,
            "data": data
        }, status=http_status.HTTP_200_OK)


class UserReportsCourseEnrollmentsView(APIView):
    """
    GET: Lấy thống kê top 5 khóa học phổ biến nhất
    Query params:
        - month: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month')
        
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                # Tạo timezone-aware datetime
                target_date = timezone.make_aware(datetime(year, month, 1))
            except:
                return Response(
                    {"detail": "Invalid month format. Use YYYY-MM"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_start = target_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
        
        from course.models import Enrollment, Course
        
        # Top 5 courses trong tháng
        top_courses = Enrollment.objects.filter(
            enrolled_at__gte=month_start,
            enrolled_at__lte=month_end
        ).values('course__title').annotate(
            enrollment_count=Count('id')
        ).order_by('-enrollment_count')[:5]
        
        labels = [item['course__title'] for item in top_courses]
        data = [item['enrollment_count'] for item in top_courses]
        
        # Nếu không đủ 5 khóa học, lấy thêm từ tất cả thời gian
        if len(labels) < 5:
            all_time_courses = Enrollment.objects.exclude(
                course__title__in=labels
            ).values('course__title').annotate(
                enrollment_count=Count('id')
            ).order_by('-enrollment_count')[:5 - len(labels)]
            
            for item in all_time_courses:
                labels.append(item['course__title'])
                data.append(item['enrollment_count'])
        
        return Response({
            "labels": labels,
            "data": data
        }, status=http_status.HTTP_200_OK)


class UserReportsContestStatsView(APIView):
    """
    GET: Lấy thống kê contest theo từng ngày trong tháng
    Query params:
        - month: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month')
        
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                # Tạo timezone-aware datetime
                target_date = timezone.make_aware(datetime(year, month, 1))
            except:
                return Response(
                    {"detail": "Invalid month format. Use YYYY-MM"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_start = target_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
        days_in_month = month_end.day
        
        from contests.models import Contest, ContestParticipant
        
        labels = []
        participants_data = []
        contest_count_data = []
        
        for day in range(1, days_in_month + 1):
            day_date = month_start.replace(day=day)
            day_end = day_date.replace(hour=23, minute=59, second=59)
            
            labels.append(f"{day:02d}/{month:02d}")
            
            # Đếm số contests bắt đầu trong ngày
            contest_count = Contest.objects.filter(
                start_at__date=day_date.date()
            ).count()
            contest_count_data.append(contest_count)
            
            # Đếm số participants đăng ký contest trong ngày
            participants_count = ContestParticipant.objects.filter(
                registered_at__date=day_date.date()
            ).count()
            participants_data.append(participants_count)
        
        return Response({
            "labels": labels,
            "contest_participants": participants_data,
            "contest_count": contest_count_data
        }, status=http_status.HTTP_200_OK)


class UserReportsTopUsersView(APIView):
    """
    GET: Lấy top 5 users xuất sắc nhất (theo rating)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from course.models import Enrollment
        
        top_users = User.objects.filter(
            deleted_at__isnull=True
        ).order_by('-current_rating')[:5]
        
        result = []
        for user in top_users:
            # Đếm số courses của user
            courses_count = Enrollment.objects.filter(user=user).count()
            
            result.append({
                "name": user.full_name or user.username,
                "username": user.username,
                "rating": user.current_rating,
                "contests": user.contests_participated,
                "courses": courses_count,
                "badge": user.rank
            })
        
        return Response(result, status=http_status.HTTP_200_OK)


class UserReportsAllUsersView(APIView):
    """
    GET: Lấy danh sách tất cả users với pagination và filter
    Query params:
        - page: page number (default: 1)
        - page_size: items per page (default: 10)
        - search: tìm kiếm theo name, username, email
        - level: filter theo rank (newbie, pupil, specialist, expert, candidate_master, master)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Pagination params
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Filter params
        search = request.query_params.get('search', '').strip()
        level = request.query_params.get('level', '').strip()
        
        # Base queryset
        queryset = User.objects.filter(deleted_at__isnull=True)
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Apply level filter
        if level and level != 'all':
            queryset = queryset.filter(rank=level)
        
        # Order by rating
        queryset = queryset.order_by('-current_rating')
        
        # Count total
        total_count = queryset.count()
        
        # Pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        users = queryset[start_index:end_index]
        
        from course.models import Enrollment
        
        result = []
        for user in users:
            # Đếm số courses
            courses_count = Enrollment.objects.filter(user=user).count()
            
            # Format dates
            join_date = user.created_at.strftime('%d/%m/%Y') if user.created_at else ''
            last_active = user.last_login_at.strftime('%d/%m/%Y') if user.last_login_at else ''
            
            # Determine user status
            user_status = 'active'
            if user.last_login_at:
                days_since_login = (timezone.now() - user.last_login_at).days
                if days_since_login > 7:
                    user_status = 'inactive'
            else:
                user_status = 'inactive'
            
            result.append({
                "id": user.id,
                "name": user.full_name or user.username,
                "username": user.username,
                "email": user.email,
                "level": user.rank,
                "rating": user.current_rating,
                "contests": user.contests_participated,
                "courses": courses_count,
                "join_date": join_date,
                "last_active": last_active,
                "status": user_status
            })
        
        return Response({
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "data": result
        }, status=http_status.HTTP_200_OK)
