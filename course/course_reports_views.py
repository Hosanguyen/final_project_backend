"""
Course Reports Views - Statistics and Analytics for Admin Dashboard
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Max, Min, Avg, Sum, F
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import Course, Enrollment, Order
from common.authentication import CustomJWTAuthentication


class CourseReportsStatsView(APIView):
    """
    GET: Lấy thống kê tổng quan khóa học theo tháng
    Query params:
        - month_year: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Lấy tháng từ query params, mặc định là tháng hiện tại
        month_str = request.query_params.get('month_year')
        
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
        
        # Tổng khóa học đến cuối tháng
        total_courses = Course.objects.filter(
            created_at__lte=month_end
        ).count()
        
        # Tổng khóa học tháng trước
        total_courses_prev = Course.objects.filter(
            created_at__lte=prev_month_end
        ).count()
        
        # Khóa học mới trong tháng
        new_courses = Course.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).count()
        
        # Khóa học mới tháng trước
        new_courses_prev = Course.objects.filter(
            created_at__gte=prev_month_start,
            created_at__lte=prev_month_end
        ).count()
        
        # Tổng đăng ký trong tháng
        total_enrollments = Enrollment.objects.filter(
            enrolled_at__gte=month_start,
            enrolled_at__lte=month_end
        ).count()
        
        # Tổng đăng ký tháng trước
        total_enrollments_prev = Enrollment.objects.filter(
            enrolled_at__gte=prev_month_start,
            enrolled_at__lte=prev_month_end
        ).count()
        
        # Tổng doanh thu trong tháng (từ orders completed)
        total_revenue = Order.objects.filter(
            status='completed',
            completed_at__gte=month_start,
            completed_at__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Tổng doanh thu tháng trước
        total_revenue_prev = Order.objects.filter(
            status='completed',
            completed_at__gte=prev_month_start,
            completed_at__lte=prev_month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Tính phần trăm thay đổi
        def calculate_change(current, previous):
            if previous == 0:
                return "+100.0%" if current > 0 else "0.0%"
            change = ((current - previous) / previous) * 100
            return f"{'+' if change >= 0 else ''}{change:.1f}%"
        
        return Response({
            "total_courses": total_courses,
            "total_change": calculate_change(total_courses, total_courses_prev),
            "new_courses": new_courses,
            "new_change": calculate_change(new_courses, new_courses_prev),
            "total_enrollments": total_enrollments,
            "enrollment_change": calculate_change(total_enrollments, total_enrollments_prev),
            "total_revenue": float(total_revenue),
            "revenue_change": calculate_change(float(total_revenue), float(total_revenue_prev))
        }, status=http_status.HTTP_200_OK)


class CourseReportsEnrollmentGrowthView(APIView):
    """
    GET: Lấy dữ liệu biểu đồ tăng trưởng đăng ký theo ngày trong tháng
    Query params:
        - month_year: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month_year')
        
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
        days_in_month = month_end.day
        
        labels = []
        total_enrollments_data = []
        new_enrollments_data = []
        
        for day in range(1, days_in_month + 1):
            day_date = month_start.replace(day=day)
            day_end = day_date.replace(hour=23, minute=59, second=59)
            
            # Label format: DD/MM
            labels.append(f"{day:02d}/{month:02d}")
            
            # Tổng enrollments đến ngày này
            total_enrollments = Enrollment.objects.filter(
                enrolled_at__lte=day_end
            ).count()
            total_enrollments_data.append(total_enrollments)
            
            # New enrollments trong ngày
            new_enrollments = Enrollment.objects.filter(
                enrolled_at__date=day_date.date()
            ).count()
            new_enrollments_data.append(new_enrollments)
        
        return Response({
            "labels": labels,
            "total_enrollments": total_enrollments_data,
            "new_enrollments": new_enrollments_data
        }, status=http_status.HTTP_200_OK)


class CourseReportsCategoryDistributionView(APIView):
    """
    GET: Lấy phân bổ khóa học theo tags/category
    Query params:
        - month_year: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month_year')
        
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
        
        from .models import Tag
        
        # Đếm số lượng courses theo tag
        tag_counts = Course.objects.filter(
            created_at__lte=month_end
        ).values('tags__name').annotate(
            count=Count('id', distinct=True)
        ).order_by('-count')
        
        # Lọc ra top 8 tags (hoặc tất cả nếu ít hơn 8)
        top_tags = [item for item in tag_counts if item['tags__name'] is not None][:8]
        
        labels = []
        data = []
        
        for item in top_tags:
            labels.append(item['tags__name'])
            data.append(item['count'])
        
        # Nếu không có data nào, trả về empty
        if not labels:
            labels = []
            data = []
        
        return Response({
            "labels": labels,
            "data": data
        }, status=http_status.HTTP_200_OK)


class CourseReportsRevenueStatsView(APIView):
    """
    GET: Lấy thống kê doanh thu theo top 5 khóa học
    Query params:
        - month_year: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month_year')
        
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
        
        # Top 5 courses theo doanh thu trong tháng
        top_courses = Order.objects.filter(
            status='completed',
            completed_at__gte=month_start,
            completed_at__lte=month_end
        ).values('course__title').annotate(
            revenue=Sum('amount')
        ).order_by('-revenue')[:5]
        
        labels = [item['course__title'] for item in top_courses]
        revenue = [float(item['revenue']) for item in top_courses]
        
        # Nếu không đủ 5 khóa học, lấy thêm từ tất cả thời gian
        if len(labels) < 5:
            all_time_courses = Order.objects.filter(
                status='completed'
            ).exclude(
                course__title__in=labels
            ).values('course__title').annotate(
                revenue=Sum('amount')
            ).order_by('-revenue')[:5 - len(labels)]
            
            for item in all_time_courses:
                labels.append(item['course__title'])
                revenue.append(float(item['revenue']))
        
        return Response({
            "labels": labels,
            "revenue": revenue
        }, status=http_status.HTTP_200_OK)


class CourseReportsCompletionStatsView(APIView):
    """
    GET: Lấy thống kê tỷ lệ hoàn thành theo top 5 khóa học
    Query params:
        - month_year: YYYY-MM format (default: current month)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        month_str = request.query_params.get('month_year')
        
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
        
        # Top 5 courses theo số lượng enrollments trong tháng
        top_courses = Enrollment.objects.filter(
            enrolled_at__gte=month_start,
            enrolled_at__lte=month_end
        ).values('course__title').annotate(
            avg_completion=Avg('progress_percent')
        ).order_by('-avg_completion')[:5]
        
        labels = [item['course__title'] for item in top_courses]
        completion_rates = [float(item['avg_completion'] or 0) for item in top_courses]
        
        # Nếu không đủ 5 khóa học, lấy thêm từ tất cả thời gian
        if len(labels) < 5:
            all_time_courses = Enrollment.objects.exclude(
                course__title__in=labels
            ).values('course__title').annotate(
                avg_completion=Avg('progress_percent')
            ).order_by('-avg_completion')[:5 - len(labels)]
            
            for item in all_time_courses:
                labels.append(item['course__title'])
                completion_rates.append(float(item['avg_completion'] or 0))
        
        return Response({
            "labels": labels,
            "completion_rates": completion_rates
        }, status=http_status.HTTP_200_OK)


class CourseReportsTopCoursesView(APIView):
    """
    GET: Lấy top 5 khóa học phổ biến nhất (theo enrollments)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Lấy top 5 courses theo enrollments
        top_courses_data = Course.objects.annotate(
            enrollment_count=Count('enrollments')
        ).order_by('-enrollment_count')[:5]
        
        result = []
        for course in top_courses_data:
            # Tính tổng doanh thu từ course
            revenue = Order.objects.filter(
                course=course,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Tính tỷ lệ hoàn thành trung bình
            avg_completion = Enrollment.objects.filter(
                course=course
            ).aggregate(avg=Avg('progress_percent'))['avg'] or 0
            
            # Lấy tag đầu tiên làm category
            category = course.tags.first().name if course.tags.exists() else 'Uncategorized'
            
            result.append({
                "title": course.title,
                "category": category,
                "price": float(course.price),
                "enrollments": course.enrollment_count,
                "revenue": float(revenue),
                "completion_rate": round(float(avg_completion), 1)
            })
        
        return Response(result, status=http_status.HTTP_200_OK)


class CourseReportsAllCoursesView(APIView):
    """
    GET: Lấy danh sách tất cả courses với pagination và filter
    Query params:
        - page: page number (default: 1)
        - page_size: items per page (default: 10)
        - search: tìm kiếm theo title
        - status: filter theo status (active, draft, archived)
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Pagination params
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Filter params
        search = request.query_params.get('search', '').strip()
        status_filter = request.query_params.get('status', '').strip()
        
        # Base queryset
        queryset = Course.objects.all()
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()
        
        # Apply status filter
        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                queryset = queryset.filter(is_published=True)
            elif status_filter == 'draft':
                queryset = queryset.filter(is_published=False)
            elif status_filter == 'archived':
                # Có thể thêm logic cho archived courses nếu cần
                queryset = queryset.none()
        
        # Order by created date
        queryset = queryset.order_by('-created_at')
        
        # Count total
        total_count = queryset.count()
        
        # Pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        courses = queryset[start_index:end_index]
        
        result = []
        for course in courses:
            # Đếm số enrollments
            enrollments_count = Enrollment.objects.filter(course=course).count()
            
            # Tính doanh thu
            revenue = Order.objects.filter(
                course=course,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Tính tỷ lệ hoàn thành
            avg_completion = Enrollment.objects.filter(
                course=course
            ).aggregate(avg=Avg('progress_percent'))['avg'] or 0
            
            # Lấy category
            category = course.tags.first().name if course.tags.exists() else 'Uncategorized'
            
            # Format dates
            created_at = course.created_at.strftime('%d/%m/%Y') if course.created_at else ''
            updated_at = course.updated_at.strftime('%d/%m/%Y') if course.updated_at else ''
            
            # Determine status
            if course.is_published:
                status = 'active'
            else:
                status = 'draft'
            
            result.append({
                "id": course.id,
                "title": course.title,
                "category": category,
                "price": float(course.price),
                "enrollments": enrollments_count,
                "revenue": float(revenue),
                "completion_rate": round(float(avg_completion), 1),
                "created_at": created_at,
                "updated_at": updated_at,
                "status": status
            })
        
        return Response({
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "data": result
        }, status=http_status.HTTP_200_OK)
