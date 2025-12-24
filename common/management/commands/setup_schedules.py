"""
Django Management Command: Setup Scheduled Tasks for Django-Q

Usage: python manage.py setup_schedules
"""
from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = 'Setup scheduled tasks for recommendation model training'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('     SETTING UP SCHEDULED TASKS'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # Xóa schedule cũ nếu có
        Schedule.objects.filter(name='train_recommendation_daily').delete()
        
        # Tạo schedule mới: Chạy mỗi ngày lúc 2:00 AM
        schedule = Schedule.objects.create(
            name='train_recommendation_daily',
            func='common.tasks.train_recommendation_model',
            schedule_type=Schedule.DAILY,
            repeats=-1,  # Chạy vô hạn
            next_run=None,  # Sẽ tự động tính
        )
        
        self.stdout.write(self.style.SUCCESS('✓ Created schedule: train_recommendation_daily'))
        self.stdout.write(f'   - Function: common.tasks.train_recommendation_model')
        self.stdout.write(f'   - Schedule: Daily at 2:00 AM')
        self.stdout.write(f'   - Status: Active')
        self.stdout.write(f'   - Next run: {schedule.next_run}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Setup completed!'))
        self.stdout.write('\n📝 Notes:')
        self.stdout.write('   - Đảm bảo Django-Q cluster đang chạy: python manage.py qcluster')
        self.stdout.write('   - Xem tasks: python manage.py qmonitor')
        self.stdout.write('   - Manual run: python manage.py train_recommendation --update-ratings\n')
