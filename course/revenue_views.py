from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, timedelta
from .models import Order
from users.models import User
from common.authentication import CustomJWTAuthentication


class RevenueStatisticsView(APIView):
    """
    API endpoint để lấy thống kê doanh thu
    Hỗ trợ lọc theo tháng: ?month=YYYY-MM
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Lấy tham số month (optional)
        month_param = request.query_params.get('month', None)
        
        # Filter orders: chỉ lấy completed orders
        orders_qs = Order.objects.filter(status='completed')
        
        # Nếu có tham số month, lọc theo tháng đó
        if month_param:
            try:
                # Parse YYYY-MM format
                year, month = map(int, month_param.split('-'))
                orders_qs = orders_qs.filter(
                    completed_at__year=year,
                    completed_at__month=month
                )
            except (ValueError, AttributeError):
                pass  # Bỏ qua nếu format không hợp lệ
        
        # Tổng doanh thu
        total_revenue = orders_qs.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Tổng số đơn hàng
        total_orders = orders_qs.count()
        
        # Số khách hàng unique
        unique_customers = orders_qs.values('user').distinct().count()
        
        # Giá trị đơn hàng trung bình
        avg_order_value = orders_qs.aggregate(
            avg=Avg('amount')
        )['avg'] or 0
        
        # Doanh thu theo ngày (30 ngày gần nhất hoặc trong tháng đã chọn)
        if month_param:
            # Nếu có filter tháng, lấy theo ngày trong tháng đó
            revenue_by_date = orders_qs.extra(
                select={'date': 'DATE(completed_at)'}
            ).values('date').annotate(
                revenue=Sum('amount'),
                orders=Count('id')
            ).order_by('date')
        else:
            # Nếu không có filter, lấy 30 ngày gần nhất
            thirty_days_ago = datetime.now() - timedelta(days=30)
            revenue_by_date = orders_qs.filter(
                completed_at__gte=thirty_days_ago
            ).extra(
                select={'date': 'DATE(completed_at)'}
            ).values('date').annotate(
                revenue=Sum('amount'),
                orders=Count('id')
            ).order_by('date')
        
        # Doanh thu theo tháng (12 tháng gần nhất)
        twelve_months_ago = datetime.now() - timedelta(days=365)
        revenue_by_month = Order.objects.filter(
            status='completed',
            completed_at__gte=twelve_months_ago
        ).extra(
            select={'month': "DATE_FORMAT(completed_at, '%%Y-%%m')"}
        ).values('month').annotate(
            revenue=Sum('amount'),
            orders=Count('id')
        ).order_by('month')
        
        # Top khóa học bán chạy
        top_courses = orders_qs.values(
            'course__id',
            'course__title',
            'course__slug'
        ).annotate(
            total_revenue=Sum('amount'),
            total_orders=Count('id')
        ).order_by('-total_revenue')[:10]
        
        # Top khách hàng (theo tổng chi tiêu)
        top_customers = orders_qs.values(
            'user__id',
            'user__username',
            'user__full_name'
        ).annotate(
            total_spent=Sum('amount'),
            total_orders=Count('id')
        ).order_by('-total_spent')[:10]
        
        # Phân bố theo phương thức thanh toán
        payment_methods = orders_qs.values('payment_method').annotate(
            revenue=Sum('amount'),
            orders=Count('id')
        ).order_by('-revenue')
        
        # Tỷ lệ thành công thanh toán
        all_orders = Order.objects.all()
        if month_param:
            try:
                year, month = map(int, month_param.split('-'))
                all_orders = all_orders.filter(
                    created_at__year=year,
                    created_at__month=month
                )
            except (ValueError, AttributeError):
                pass
        
        total_all = all_orders.count()
        total_completed = all_orders.filter(status='completed').count()
        total_failed = all_orders.filter(status='failed').count()
        total_pending = all_orders.filter(status='pending').count()
        total_cancelled = all_orders.filter(status='cancelled').count()
        
        success_rate = (total_completed / total_all * 100) if total_all > 0 else 0
        
        return Response({
            # Tổng quan
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'unique_customers': unique_customers,
            'avg_order_value': float(avg_order_value),
            'success_rate': round(success_rate, 2),
            
            # Biểu đồ theo ngày
            'revenue_by_date': list(revenue_by_date),
            
            # Biểu đồ theo tháng
            'revenue_by_month': list(revenue_by_month),
            
            # Top courses
            'top_courses': list(top_courses),
            
            # Top customers
            'top_customers': list(top_customers),
            
            # Payment methods
            'payment_methods': list(payment_methods),
            
            # Order status distribution
            'order_status': {
                'completed': total_completed,
                'failed': total_failed,
                'pending': total_pending,
                'cancelled': total_cancelled
            }
        })
