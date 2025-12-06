from django.contrib import admin
from .models import Language, Tag, File, Course, Lesson, LessonResource, Enrollment, Order

# Register your models here.

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'active', 'created_at']
    list_filter = ['active']
    search_fields = ['name', 'code']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'created_at']
    search_fields = ['name', 'slug']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'slug', 'level', 'price', 'is_published', 'created_at']
    list_filter = ['level', 'is_published']
    search_fields = ['title', 'slug']
    filter_horizontal = ['languages', 'tags']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'course', 'sequence', 'created_at']
    list_filter = ['course']
    search_fields = ['title']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'course', 'enrolled_at', 'progress_percent']
    list_filter = ['enrolled_at']
    search_fields = ['user__username', 'course__title']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_code', 'user', 'course', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_code', 'user__username', 'course__title', 'vnp_txn_ref', 'vnp_transaction_no']
    readonly_fields = ['order_code', 'vnp_txn_ref', 'vnp_transaction_no', 'vnp_response_code', 
                      'vnp_bank_code', 'vnp_pay_date', 'created_at', 'updated_at', 'completed_at']

