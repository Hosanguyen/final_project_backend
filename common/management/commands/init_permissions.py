from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone
from datetime import timedelta
# app_name/apps.py

def get_model_list():
    hide_apps = ['admin', 'auth', 'contenttypes', 'sessions']
    hide_db_name = []
    models = [
        model._meta.db_table
        for model in apps.get_models() 
            if model._meta.app_label not in hide_apps \
            and model._meta.db_table not in hide_db_name
    ]
    return models

def create_default_roles(sender, **kwargs):
    from users.models import Role
    
    Role.objects.get_or_create(
        name="admin",
        defaults={
            "is_default": True,
            "description": "Administrator with full permissions"
        }
    )
    Role.objects.get_or_create(
        name="user",
        defaults={
            "is_default": True,
            "description": "User with limited permissions"
        }
    )

def create_default_permissions(sender, **kwargs):
    from users.models import Permission, PermissionCategory
    
    model_list = get_model_list()
    
    # Create categories based on model grouping (using db_table names)
    categories = {
        "User Management": ["roles", "permissions", "permission_categories", "role_permissions", "users", "user_roles", "revoked_tokens"],
        "Content Management": ["tags", "languages", "files"],
        "Course Management": ["courses", "lessons", "lesson_resources", "enrollments"],
        "Problem Management": ["problems", "tags_problems", "test_cases", "submissions"],
        "Contest Management": ["contests", "contest_problems", "contest_participants"],
        "Quiz Management": ["quizzes", "quiz_questions", "quiz_options", "quiz_submissions", "quiz_answers"],
        "Other": []
    }
    
    # Create permission categories
    created_categories = {}
    for category_name, models in categories.items():
        category, _ = PermissionCategory.objects.get_or_create(
            name=category_name,
            defaults={
                "description": f"Permissions related to {category_name.lower()}"
            }
        )
        created_categories[category_name] = category
    
    # Create permissions for each model
    permission_types = [
        ("create", "Create"),
        ("read", "Read/View"),
        ("update", "Update/Edit"),
        ("delete", "Delete")
    ]
    
    for model_name in model_list:
        # Find which category this model belongs to
        category = None
        for cat_name, models in categories.items():
            if model_name in models:
                category = created_categories[cat_name]
                break
        if category is None:
            category = created_categories["Other"]
        # Create permissions for this model
        for perm_code, perm_desc in permission_types:
            code = f"{model_name}.{perm_code}"
            Permission.objects.get_or_create(
                code=code,
                defaults={
                    "description": f"{perm_desc} {model_name}",
                    "model_name": model_name,
                    "perm": perm_code,
                    "category": category
                }
            )

def create_default_role_permissions(sender, **kwargs):
    from users.models import Role, Permission, RolePermission
    
    # Get admin role
    admin_role = Role.objects.filter(name="admin").first()
    if not admin_role:
        return
    
    # Get all permissions
    all_permissions = Permission.objects.all()
    
    # Assign all permissions to admin role
    for permission in all_permissions:
        RolePermission.objects.get_or_create(
            role=admin_role,
            permission=permission
        )
    
    # Get user role
    user_role = Role.objects.filter(name="user").first()
    if not user_role:
        return
    
    # Define read-only permissions for user role
    user_allowed_permissions = [
        # Content - read only
        "tags.read",
        "languages.read",
        "files.read",
        # Course - read and create enrollments
        "courses.read",
        "lessons.read",
        "lesson_resources.read",
        "enrollments.create",
        "enrollments.read",
        "enrollments.delete",  # can unenroll
        # Problem - read and submit
        "problems.read",
        "test_cases.read",
        "submissions.create",
        "submissions.read",
        # Contest - read and participate
        "contests.read",
        "contest_problems.read",
        "contest_participants.create",
        "contest_participants.read",
        "contest_participants.delete",
        # Quiz - read and submit
        "quizzes.read",
        "quiz_questions.read",
        "quiz_options.read",
        "quiz_submissions.create",
        "quiz_submissions.read",
        "quiz_answers.create",
        "quiz_answers.read",
        # User - can update own profile
        "users.read",
        "users.update",
    ]
    
    # Assign specific permissions to user role
    for perm_code in user_allowed_permissions:
        permission = Permission.objects.filter(code=perm_code).first()
        if permission:
            RolePermission.objects.get_or_create(
                role=user_role,
                permission=permission
            )

def create_default_admin_user(sender, **kwargs):
    """Create default admin user and assign admin role"""
    from users.models import User, Role, UserRole
    import os
    
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    
    # Create admin user if not exists
    if not User.objects.filter(username=username).exists():
        user = User.objects.create(
            username=username,
            email=email
        )
        user.set_password(password)
        user.save()
        print(f"Admin user '{username}' created successfully!")
    else:
        user = User.objects.get(username=username)
        print(f"Admin user '{username}' already exists")
    
    # Assign admin role to user
    admin_role = Role.objects.filter(name="admin").first()
    if admin_role:
        UserRole.objects.get_or_create(
            user=user,
            role=admin_role
        )
        print(f"Admin role assigned to user '{username}'")

def create_practice_contest(sender, **kwargs):
    """Create a practice contest and sync with DOMjudge"""
    from contests.models import Contest
    from contests.domjudge_service import DOMjudgeContestService
    from common.connection import execute_raw_query
    
    # Check if practice contest already exists in local database
    if Contest.objects.filter(slug="practice").exists():
        return
    
    # Create practice contest
    now = timezone.now()
    # Set start time to current time (not in past - DOMjudge might not accept past dates)
    start_time = now
    # Set end time to 2 years from now for practice
    end_time = now + timedelta(days=365 * 2)
    
    practice_contest = Contest.objects.create(
        slug="practice",
        title="Practice Contest",
        description="A permanent contest for practicing problems",
        start_at=start_time,
        end_at=end_time,
        visibility="public",
        contest_mode="OI",
        is_show_result=True,
        penalty_time=0,
        penalty_mode="standard",
        freeze_rankings_at=None
    )
    
    # Check if contest with externalid='practice' already exists in DOMjudge
    try:
        check_query = """
            SELECT cid, externalid, name 
            FROM contest 
            WHERE externalid = %s
        """
        existing_contests = execute_raw_query('domjudge', check_query, ['practice'], fetch=True)
        
        if existing_contests and len(existing_contests) > 0:
            # Contest already exists in DOMjudge, skip sync
            print(f"Practice contest already exists in DOMjudge (cid: {existing_contests[0]['cid']}), skipping sync")
            return
        
        # Contest doesn't exist in DOMjudge, proceed with sync
        domjudge_service = DOMjudgeContestService()
        
        # Calculate duration (2 years in hours)
        duration_hours = 365 * 2 * 24
        duration_str = f"{duration_hours}:00:00"
        
        # Format start_time for DOMjudge (must match format: YYYY-MM-DD HH:MM:SS UTC)
        # Convert to UTC and format without timezone info
        from django.utils import timezone as tz
        start_utc = practice_contest.start_at.astimezone(tz.utc)
        start_time_str = start_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        contest_data = {
            'id': practice_contest.slug,
            'name': practice_contest.title,
            'formal_name': practice_contest.title,
            'start_time': start_time_str,
            'duration': duration_str,
            'penalty_time': practice_contest.penalty_time
        }
        
        domjudge_service.create_contest(contest_data)
        print("Practice contest successfully synced with DOMjudge")
        
    except Exception as e:
        # If DOMjudge sync fails, still keep the local contest
        print(f"Warning: Failed to sync practice contest with DOMjudge: {str(e)}")
        print("Practice contest created locally but not synced with DOMjudge")

class Command(BaseCommand):
    help = 'Initialize default roles, permissions and categories'

    def handle(self, *args, **options):
        
        self.stdout.write('Creating default roles...')
        create_default_roles(sender=None)
        self.stdout.write(self.style.SUCCESS('✓ Default roles created'))
        
        self.stdout.write('Creating default permissions and categories...')
        create_default_permissions(sender=None)
        self.stdout.write(self.style.SUCCESS('✓ Default permissions and categories created'))
        
        self.stdout.write('Assigning permissions to roles...')
        create_default_role_permissions(sender=None)
        self.stdout.write(self.style.SUCCESS('✓ Role permissions assigned'))
        
        self.stdout.write('Creating default admin user...')
        create_default_admin_user(sender=None)
        self.stdout.write(self.style.SUCCESS('✓ Admin user created and assigned admin role'))
        
        self.stdout.write('Creating practice contest...')
        create_practice_contest(sender=None)
        self.stdout.write(self.style.SUCCESS('✓ Practice contest created and synced with DOMjudge'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Initialization completed successfully!'))
