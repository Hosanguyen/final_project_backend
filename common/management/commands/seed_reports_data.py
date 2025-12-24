"""
Django Management Command để seed dữ liệu cho User Reports và Course Reports
Chạy: python manage.py seed_reports_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
import random

from users.models import User
from course.models import Course, Tag, Language, Enrollment, Order
from contests.models import Contest, ContestParticipant


class Command(BaseCommand):
    help = 'Seed fake data for User Reports and Course Reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months of historical data to generate (default: 6)',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=100,
            help='Number of users to create (default: 100)',
        )
        parser.add_argument(
            '--courses',
            type=int,
            default=20,
            help='Number of courses to create (default: 20)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        months = options['months']
        num_users = options['users']
        num_courses = options['courses']
        clear_data = options['clear']

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Starting Reports Data Seeding'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        if clear_data:
            self.clear_existing_data()

        try:
            with transaction.atomic():
                # Step 1: Create Tags and Languages
                tags = self.create_tags()
                languages = self.create_languages()
                
                # Step 2: Create Users
                users = self.create_users(num_users, months)
                
                # Step 3: Create Courses
                courses = self.create_courses(num_courses, tags, languages, months)
                
                # Step 4: Create Enrollments
                self.create_enrollments(users, courses, months)
                
                # Step 5: Create Orders (payments)
                self.create_orders(users, courses, months)
                
                # Step 6: Create Contests
                contests = self.create_contests(months)
                
                # Step 7: Create Contest Participants
                self.create_contest_participants(users, contests, months)
                
                self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
                self.stdout.write(self.style.SUCCESS('✓ Seeding completed successfully!'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error during seeding: {str(e)}'))
            raise

    def clear_existing_data(self):
        """Xóa dữ liệu hiện có (cẩn thận!)"""
        self.stdout.write(self.style.WARNING('\nClearing existing data...'))
        
        # Xóa theo thứ tự dependencies
        ContestParticipant.objects.all().delete()
        Contest.objects.all().delete()
        Order.objects.all().delete()
        Enrollment.objects.all().delete()
        Course.objects.all().delete()
        Tag.objects.all().delete()
        Language.objects.all().delete()
        # Không xóa users vì có thể có admin user
        
        self.stdout.write(self.style.SUCCESS('✓ Data cleared'))

    def create_tags(self):
        """Tạo tags cho courses"""
        self.stdout.write('\n1. Creating tags...')
        
        tag_names = [
            'Python', 'JavaScript', 'Java', 'C++', 'Data Structures',
            'Algorithms', 'Web Development', 'Machine Learning', 'AI',
            'Database', 'DevOps', 'Mobile Development', 'Security',
            'Cloud Computing', 'Design Patterns', 'Testing'
        ]
        
        tags = []
        for name in tag_names:
            tag, created = Tag.objects.get_or_create(
                name=name,
                defaults={'slug': name.lower().replace(' ', '-')}
            )
            tags.append(tag)
            if created:
                self.stdout.write(f'  • Created tag: {name}')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(tags)} tags'))
        return tags

    def create_languages(self):
        """Tạo programming languages"""
        self.stdout.write('\n2. Creating languages...')
        
        lang_data = [
            ('python', 'Python', '.py'),
            ('javascript', 'JavaScript', '.js'),
            ('java', 'Java', '.java'),
            ('cpp', 'C++', '.cpp'),
            ('csharp', 'C#', '.cs'),
            ('go', 'Go', '.go'),
            ('rust', 'Rust', '.rs'),
        ]
        
        languages = []
        for code, name, ext in lang_data:
            lang, created = Language.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'extension': ext,
                    'active': True
                }
            )
            languages.append(lang)
            if created:
                self.stdout.write(f'  • Created language: {name}')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(languages)} languages'))
        return languages

    def create_users(self, count, months):
        """Tạo users với timestamps phân bổ qua các tháng"""
        self.stdout.write(f'\n3. Creating {count} users...')
        
        ranks = [choice[0] for choice in User.RANK_CHOICES]
        now = timezone.now()
        users = []
        
        # Không cần admin user cho việc tạo users
        # admin_user = User.objects.first()
        
        for i in range(count):
            # Random created_at trong khoảng months tháng
            days_ago = random.randint(0, months * 30)
            created_at = now - timedelta(days=days_ago)
            
            # Random last_login trong khoảng từ created_at đến now
            if random.random() > 0.2:  # 80% users có last_login
                last_login_days = random.randint(0, (now - created_at).days) if (now - created_at).days > 0 else 0
                last_login = created_at + timedelta(days=last_login_days)
            else:
                last_login = None
            
            # Random rating và rank
            rating = random.randint(800, 2500)
            rank = random.choice(ranks)
            contests_participated = random.randint(0, 50)
            
            username = f'user_{i+1:04d}'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'full_name': f'User {i+1}',
                    'current_rating': rating,
                    'rank': rank,
                    'contests_participated': contests_participated,
                    'created_at': created_at,
                    'last_login_at': last_login,
                }
            )
            
            if created:
                user.set_password('password123')
                user.created_at = created_at  # Override auto_now_add
                user.save()
                users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(users)} users'))
        return users

    def create_courses(self, count, tags, languages, months):
        """Tạo courses với timestamps phân bổ"""
        self.stdout.write(f'\n4. Creating {count} courses...')
        
        course_titles = [
            'Python for Beginners', 'Advanced JavaScript', 'Data Structures in Java',
            'Web Development Bootcamp', 'Machine Learning A-Z', 'React Masterclass',
            'Angular Complete Guide', 'Vue.js Essential Training', 'Node.js Backend',
            'Django Web Framework', 'Flask REST API', 'Spring Boot Microservices',
            'AWS Cloud Practitioner', 'Docker and Kubernetes', 'CI/CD Pipeline',
            'Algorithm Design', 'System Design Interview', 'Database Design',
            'MongoDB Complete Course', 'PostgreSQL Advanced'
        ]
        
        levels = ['beginner', 'intermediate', 'advanced']
        now = timezone.now()
        courses = []
        
        # Lấy user đầu tiên để làm creator, hoặc tạo một user mới nếu chưa có
        admin_user = User.objects.first()
        if not admin_user:
            admin_user = User.objects.create(
                username='course_creator',
                email='creator@example.com',
                full_name='Course Creator',
                current_rating=1500,
                rank='specialist'
            )
            admin_user.set_password('password123')
            admin_user.save()
        
        for i in range(count):
            title = course_titles[i] if i < len(course_titles) else f'Course {i+1}'
            
            # Random created_at
            days_ago = random.randint(0, months * 30)
            created_at = now - timedelta(days=days_ago)
            
            # Random price
            price = Decimal(random.choice([0, 99000, 199000, 299000, 499000, 999000]))
            
            course, created = Course.objects.get_or_create(
                slug=title.lower().replace(' ', '-') + f'-{i}',
                defaults={
                    'title': title,
                    'short_description': f'Learn {title} from scratch',
                    'long_description': f'Complete guide to {title}',
                    'level': random.choice(levels),
                    'price': price,
                    'is_published': random.random() > 0.1,  # 90% published
                    'created_by': admin_user,
                    'created_at': created_at,
                }
            )
            
            if created:
                # Thêm tags (2-4 tags mỗi course)
                course_tags = random.sample(tags, random.randint(2, min(4, len(tags))))
                course.tags.set(course_tags)
                
                # Thêm languages (1-2 languages)
                course_langs = random.sample(languages, random.randint(1, min(2, len(languages))))
                course.languages.set(course_langs)
                
                course.created_at = created_at
                course.save()
                courses.append(course)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(courses)} courses'))
        return courses

    def create_enrollments(self, users, courses, months):
        """Tạo enrollments với timestamps phân bổ"""
        self.stdout.write(f'\n5. Creating enrollments...')
        
        now = timezone.now()
        enrollment_count = 0
        
        for user in users:
            # Mỗi user đăng ký 1-5 courses
            num_enrollments = random.randint(1, 5)
            user_courses = random.sample(courses, min(num_enrollments, len(courses)))
            
            for course in user_courses:
                # Enrollment date phải sau cả user created và course created
                earliest_date = max(user.created_at, course.created_at)
                days_range = (now - earliest_date).days
                
                if days_range > 0:
                    days_after = random.randint(0, days_range)
                    enrolled_at = earliest_date + timedelta(days=days_after)
                else:
                    enrolled_at = earliest_date
                
                # Random progress
                progress = Decimal(random.uniform(0, 100))
                
                # Random last_accessed
                if random.random() > 0.3:  # 70% có last_accessed
                    access_days = random.randint(0, (now - enrolled_at).days) if (now - enrolled_at).days > 0 else 0
                    last_accessed = enrolled_at + timedelta(days=access_days)
                else:
                    last_accessed = None
                
                enrollment, created = Enrollment.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={
                        'enrolled_at': enrolled_at,
                        'progress_percent': progress,
                        'last_accessed_at': last_accessed,
                    }
                )
                
                if created:
                    enrollment.enrolled_at = enrolled_at
                    enrollment.save()
                    enrollment_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {enrollment_count} enrollments'))

    def create_orders(self, users, courses, months):
        """Tạo orders (payments)"""
        self.stdout.write(f'\n6. Creating orders...')
        
        now = timezone.now()
        order_count = 0
        
        # Lấy các enrollments đã tạo
        enrollments = Enrollment.objects.select_related('user', 'course').all()
        
        for enrollment in enrollments:
            # 80% enrollments có order (20% là free courses)
            if enrollment.course.price > 0 and random.random() > 0.2:
                order_code = f'ORD-{enrollment.user.id}-{enrollment.course.id}-{random.randint(1000, 9999)}'
                
                # Order completed_at gần với enrollment enrolled_at
                completed_at = enrollment.enrolled_at - timedelta(minutes=random.randint(1, 30))
                
                order, created = Order.objects.get_or_create(
                    order_code=order_code,
                    defaults={
                        'user': enrollment.user,
                        'course': enrollment.course,
                        'amount': enrollment.course.price,
                        'status': 'completed',
                        'payment_method': 'vnpay',
                        'vnp_txn_ref': f'TXN{random.randint(100000, 999999)}',
                        'vnp_transaction_no': f'{random.randint(10000000, 99999999)}',
                        'vnp_response_code': '00',
                        'created_at': completed_at - timedelta(minutes=5),
                        'completed_at': completed_at,
                    }
                )
                
                if created:
                    order.created_at = completed_at - timedelta(minutes=5)
                    order.completed_at = completed_at
                    order.save()
                    order_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {order_count} orders'))

    def create_contests(self, months):
        """Tạo contests"""
        self.stdout.write(f'\n7. Creating contests...')
        
        now = timezone.now()
        contests = []
        
        contest_names = [
            'Weekly Contest', 'Algorithm Marathon', 'Speed Coding Challenge',
            'Data Structure Showdown', 'Competitive Programming Round',
            'CodeForces Style Contest', 'LeetCode Weekly', 'HackerRank Challenge'
        ]
        
        # Lấy user để làm creator
        creator = User.objects.first()
        if not creator:
            creator = User.objects.create(
                username='contest_creator',
                email='contest_creator@example.com',
                full_name='Contest Creator',
                current_rating=1500,
                rank='specialist'
            )
            creator.set_password('password123')
            creator.save()
        
        # Tạo contests trong khoảng months tháng
        for i in range(months * 4):  # 4 contests per month
            title = f"{random.choice(contest_names)} #{i+1}"
            slug = title.lower().replace(' ', '-').replace('#', '') + f'-{i+1}'
            
            days_ago = random.randint(0, months * 30)
            start_at = now - timedelta(days=days_ago)
            end_at = start_at + timedelta(hours=random.randint(2, 6))
            
            contest = Contest.objects.create(
                title=title,
                slug=slug,
                description=f'Description for {title}',
                start_at=start_at,
                end_at=end_at,
                visibility='public',
                contest_mode=random.choice(['ICPC', 'OI']),
                created_by=creator,
            )
            contests.append(contest)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(contests)} contests'))
        return contests

    def create_contest_participants(self, users, contests, months):
        """Tạo contest participants"""
        self.stdout.write(f'\n8. Creating contest participants...')
        
        participant_count = 0
        
        for contest in contests:
            # Mỗi contest có 10-50 participants
            num_participants = random.randint(10, min(50, len(users)))
            contest_users = random.sample(users, num_participants)
            
            for user in contest_users:
                # Chỉ tạo participant nếu user đã tồn tại trước contest
                if user.created_at < contest.start_at:
                    registered_at = contest.start_at - timedelta(days=random.randint(1, 7))
                    
                    participant, created = ContestParticipant.objects.get_or_create(
                        user=user,
                        contest=contest,
                        defaults={
                            'registered_at': registered_at,
                        }
                    )
                    
                    if created:
                        participant.registered_at = registered_at
                        participant.save()
                        participant_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {participant_count} contest participants'))
