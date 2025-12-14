from django.urls import path
from .views import (
    LanguageView, LanguageDetailView,
    CourseView, CourseDetailView,
    LessonView, LessonDetailView,
    LessonResourceView, LessonResourceDetailView,
    TagView, TagDetailView,
    CreatePaymentView, VNPayReturnView, CheckPaymentStatusView,
    OrderHistoryView, CheckEnrollmentView, EnrollmentListView
)
from .course_reports_views import (
    CourseReportsStatsView,
    CourseReportsEnrollmentGrowthView,
    CourseReportsCategoryDistributionView,
    CourseReportsRevenueStatsView,
    CourseReportsCompletionStatsView,
    CourseReportsTopCoursesView,
    CourseReportsAllCoursesView
)

urlpatterns = [
    # Language URLs
    path("languages/", LanguageView.as_view(), name="language-list-create"),
    path("languages/<int:pk>/", LanguageDetailView.as_view(), name="language-detail"),
    
    # Course URLs
    path("courses/", CourseView.as_view(), name="course-list-create"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/slug/<slug:slug>/", CourseDetailView.as_view(), name="course-detail-by-slug"),
    
    # Lesson URLs
    path("lessons/", LessonView.as_view(), name="lesson-list-create"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    
    # Lesson Resource URLs
    path("lesson-resources/", LessonResourceView.as_view(), name="lesson-resource-list-create"),
    path("lesson-resources/<int:pk>/", LessonResourceDetailView.as_view(), name="lesson-resource-detail"),
    
    # Tag URLs
    path("tags/", TagView.as_view(), name="tag-list-create"),
    path("tags/<int:pk>/", TagDetailView.as_view(), name="tag-detail"),
    
    # Payment URLs
    path("payment/create/", CreatePaymentView.as_view(), name="create-payment"),
    path("payment/vnpay/return/", VNPayReturnView.as_view(), name="vnpay-return"),
    path("payment/status/<str:order_code>/", CheckPaymentStatusView.as_view(), name="check-payment-status"),
    path("payment/history/", OrderHistoryView.as_view(), name="order-history"),
    
    # Enrollment URLs
    path("enrollment/check/<int:course_id>/", CheckEnrollmentView.as_view(), name="check-enrollment"),
    path("enrollment/list/", EnrollmentListView.as_view(), name="enrollment-list"),
    
    # Reports URLs
    path("courses/reports/stats/", CourseReportsStatsView.as_view(), name="course-reports-stats"),
    path("courses/reports/top-courses/", CourseReportsTopCoursesView.as_view(), name="course-reports-top-courses"),
    path("courses/reports/all-courses/", CourseReportsAllCoursesView.as_view(), name="course-reports-all-courses"),
    path("courses/reports/enrollment-growth/", CourseReportsEnrollmentGrowthView.as_view(), name="course-reports-enrollment-growth"),
    path("courses/reports/category-distribution/", CourseReportsCategoryDistributionView.as_view(), name="course-reports-category-distribution"),
    path("courses/reports/revenue-stats/", CourseReportsRevenueStatsView.as_view(), name="course-reports-revenue-stats"),
    path("courses/reports/completion-stats/", CourseReportsCompletionStatsView.as_view(), name="course-reports-completion-stats"),
]
