"""
Django Management Command: Fake Data Generator
Tạo dữ liệu giả cho hệ thống gồm:
- 200 Problems (có test cases, sync với DOMjudge)
- 100 Users (có rating)
- 10000 Submissions (AC/WA/TLE...)

Usage: python manage.py fake_data [--problems 200] [--users 100] [--submissions 10000]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import random
import time
from faker import Faker

from problems.models import Problem, TestCase, Submissions, TagProblem
from course.models import Tag, Language
from users.models import User, Role
from problems.domjudge_service import DOMjudgeService


class DataFaker:
    def __init__(self):
        self.fake = Faker(['en_US'])
        self.tags_pool = [
            'dp', 'graph', 'math', 'greedy', 'string', 
            'data-structures', 'geometry', 'implementation', 
            'binary-search', 'two-pointers', 'dfs', 'bfs', 
            'tree', 'bit-manipulation', 'sorting', 'hashing',
            'number-theory', 'brute-force', 'divide-conquer',
            'backtracking'
        ]
        self.submission_statuses = ['ac', 'wa', 'tle', 'mle', 're', 'ce']
        self.languages = []
        self.tags = []
        self.users = []
        self.problems = []
        
    def setup_prerequisites(self):
        """Tạo hoặc lấy Languages và Tags"""
        print("   -> Setting up Languages and Tags...")
        
        # Ensure languages exist
        language_data = [
            {'code': 'python', 'name': 'Python 3', 'externalid': 'python3', 'extension': '.py'},
            {'code': 'java', 'name': 'Java', 'externalid': 'java', 'extension': '.java'},
            {'code': 'cpp', 'name': 'C++', 'externalid': 'cpp', 'extension': '.cpp'},
            {'code': 'c', 'name': 'C', 'externalid': 'c', 'extension': '.c'},
            {'code': 'javascript', 'name': 'JavaScript', 'externalid': 'javascript', 'extension': '.js'},
        ]
        
        for lang_data in language_data:
            lang, created = Language.objects.get_or_create(
                code=lang_data['code'],
                defaults=lang_data
            )
            self.languages.append(lang)
        
        # Ensure tags exist
        for tag_name in self.tags_pool:
            tag, created = Tag.objects.get_or_create(
                slug=tag_name,
                defaults={'name': tag_name.replace('-', ' ').title()}
            )
            self.tags.append(tag)
        
        print(f"      ✓ {len(self.languages)} languages, {len(self.tags)} tags ready")
    
    def generate_users(self, count=100):
        """Tạo fake users với rating phân bố thực tế"""
        print(f"\n[1/4] Generating {count} users...")
        
        # Đảm bảo có role Student
        student_role, _ = Role.objects.get_or_create(
            name='Student',
            defaults={'description': 'Student role', 'is_default': True}
        )
        
        created_users = []
        
        with transaction.atomic():
            for i in range(count):
                # Generate unique username bằng faker
                username = self.fake.unique.user_name()
                
                # Phân bố rating giống thực tế (skewed distribution)
                # 40% newbie (800-1199), 25% pupil (1200-1399), 20% specialist, 10% expert, 5% cao hơn
                rand = random.random()
                if rand < 0.4:
                    rating = random.randint(800, 1199)
                    rank = 'newbie'
                elif rand < 0.65:
                    rating = random.randint(1200, 1399)
                    rank = 'pupil'
                elif rand < 0.85:
                    rating = random.randint(1400, 1599)
                    rank = 'specialist'
                elif rand < 0.95:
                    rating = random.randint(1600, 1899)
                    rank = 'expert'
                else:
                    rating = random.randint(1900, 2500)
                    if rating < 2100:
                        rank = 'candidate_master'
                    elif rating < 2300:
                        rank = 'master'
                    else:
                        rank = 'international_master'
                
                user = User.objects.create(
                    username=username,
                    email=f"{username}@example.com",
                    password='pbkdf2_sha256$260000$test$fake',  # dummy hashed password
                    full_name=self.fake.name(),
                    current_rating=rating,
                    max_rating=rating + random.randint(0, 200),
                    rank=rank,
                    max_rank=rank,
                    contests_participated=random.randint(0, 50),
                    total_problems_solved=0,  # Sẽ update sau khi tạo submissions
                    rating_volatility=max(50, 350 - random.randint(0, 100)),
                    active=True
                )
                
                # Gán role
                user.roles.add(student_role)
                created_users.append(user)
                
                if (i + 1) % 20 == 0:
                    print(f"      Progress: {i + 1}/{count} users...")
        
        self.users = created_users
        print(f"   ✓ Created {len(created_users)} users")
        return created_users
    
    def generate_problems(self, count=200, sync_to_domjudge=True):
        """Tạo fake problems với test cases"""
        print(f"\n[2/4] Generating {count} problems...")
        
        created_problems = []
        domjudge_service = DOMjudgeService()
        
        # Lấy admin user để gán created_by
        admin_user = User.objects.filter(username='admin').first()
        
        for i in range(count):
            with transaction.atomic():
                # Random rating theo phân bố
                rating = random.choice(range(800, 3000, 100))
                if rating < 1400:
                    difficulty = 'easy'
                elif rating < 2100:
                    difficulty = 'medium'
                else:
                    difficulty = 'hard'
                
                # Tạo problem
                problem = Problem.objects.create(
                    slug=f"problem-{i+1:04d}",
                    title=f"Problem {i+1}: {self.fake.catch_phrase()}",
                    short_statement=self.fake.sentence(),
                    statement_text=self._generate_problem_statement(),
                    input_format="Standard input with test cases",
                    output_format="Standard output with results",
                    difficulty=difficulty,
                    rating=rating,
                    time_limit_ms=random.choice([1000, 2000, 3000, 5000]),
                    memory_limit_kb=262144,
                    source=f"Mock Contest {random.randint(1, 50)}",
                    is_public=True,
                    created_by=admin_user,
                    updated_by=admin_user
                )
                
                # Gán ngẫu nhiên 2-4 tags
                problem_tags = random.sample(self.tags, random.randint(2, 4))
                for tag in problem_tags:
                    TagProblem.objects.create(tag=tag, problem=problem)
                
                # Gán allowed languages (2-3 languages)
                allowed_langs = random.sample(self.languages, random.randint(2, 3))
                problem.allowed_languages.set(allowed_langs)
                
                # Tạo test cases (2 sample + 8-12 secret)
                self._create_test_cases(problem)
                
                created_problems.append(problem)
                
                # Sync với DOMjudge
                if sync_to_domjudge:
                    try:
                        domjudge_id = domjudge_service.sync_problem(problem)
                        problem.domjudge_problem_id = domjudge_id
                        problem.is_synced_to_domjudge = True
                        problem.last_synced_at = timezone.now()
                        problem.save()
                        print(f"      ✓ [{i+1}/{count}] {problem.slug} synced to DOMjudge: {domjudge_id}")
                    except Exception as e:
                        print(f"      ✗ [{i+1}/{count}] {problem.slug} sync failed: {str(e)}")
                        # Vẫn giữ problem nhưng không sync
                        problem.is_synced_to_domjudge = False
                        problem.save()
                else:
                    print(f"      ✓ [{i+1}/{count}] {problem.slug} created (skip sync)")
        
        self.problems = created_problems
        print(f"   ✓ Created {len(created_problems)} problems")
        return created_problems
    
    def _generate_problem_statement(self):
        """Tạo đề bài giả HTML"""
        return f"""
<h2>Problem Statement</h2>
<p>{self.fake.paragraph()}</p>

<h3>Input</h3>
<p>{self.fake.sentence()}</p>

<h3>Output</h3>
<p>{self.fake.sentence()}</p>

<h3>Constraints</h3>
<ul>
    <li>1 ≤ N ≤ 10<sup>5</sup></li>
    <li>Time limit: 2 seconds</li>
</ul>
"""
    
    def _create_test_cases(self, problem):
        """Tạo test cases cho problem"""
        # 2 sample tests
        for seq in range(1, 3):
            TestCase.objects.create(
                problem=problem,
                type='sample',
                sequence=seq,
                input_data=self._generate_test_input(),
                output_data=self._generate_test_output(),
                points=0  # Sample không tính điểm
            )
        
        # 8-12 secret tests
        num_secret = random.randint(8, 12)
        for seq in range(3, 3 + num_secret):
            TestCase.objects.create(
                problem=problem,
                type='secret',
                sequence=seq,
                input_data=self._generate_test_input(),
                output_data=self._generate_test_output(),
                points=10.0
            )
    
    def _generate_test_input(self):
        """Tạo test input giả"""
        n = random.randint(1, 100)
        values = [random.randint(1, 1000) for _ in range(n)]
        return f"{n}\n{' '.join(map(str, values))}"
    
    def _generate_test_output(self):
        """Tạo test output giả"""
        result = random.randint(1, 100000)
        return str(result)
    
    def generate_submissions(self, count=10000):
        """Tạo fake submissions"""
        print(f"\n[3/4] Generating {count} submissions...")
        
        if not self.users or not self.problems:
            print("   ✗ Need users and problems first!")
            return []
        
        created_submissions = []
        user_solved_count = {user.id: 0 for user in self.users}
        
        with transaction.atomic():
            for i in range(count):
                # Random user
                user = random.choice(self.users)
                
                # Chọn problem theo skill user
                # User có xu hướng giải bài gần với rating của họ
                user_rating = user.current_rating
                
                # Filter problems trong khoảng rating phù hợp
                suitable_problems = [
                    p for p in self.problems 
                    if abs(p.rating - user_rating) <= 400
                ]
                
                if not suitable_problems:
                    suitable_problems = self.problems
                
                problem = random.choice(suitable_problems)
                language = random.choice(list(problem.allowed_languages.all()))
                
                # Tính xác suất AC dựa trên skill gap
                rating_diff = problem.rating - user_rating
                if rating_diff < -200:
                    ac_prob = 0.9  # Bài dễ hơn nhiều
                elif rating_diff < 0:
                    ac_prob = 0.7
                elif rating_diff < 200:
                    ac_prob = 0.5
                elif rating_diff < 400:
                    ac_prob = 0.3
                else:
                    ac_prob = 0.15  # Bài khó hơn nhiều
                
                # Random status theo xác suất
                if random.random() < ac_prob:
                    status = 'ac'
                    score = 100.0
                    test_passed = problem.test_cases.count()
                    user_solved_count[user.id] += 1
                else:
                    # Các loại lỗi khác
                    error_types = ['wa', 'wa', 'wa', 'tle', 'mle', 're', 'ce']
                    status = random.choice(error_types)
                    test_passed = random.randint(0, problem.test_cases.count() - 1)
                    score = (test_passed / problem.test_cases.count()) * 100 if problem.test_cases.count() > 0 else 0
                
                # Tạo submission
                submission = Submissions.objects.create(
                    problem=problem,
                    user=user,
                    language=language,
                    code_text=self._generate_fake_code(language.code),
                    status=status,
                    score=score,
                    test_passed=test_passed,
                    test_total=problem.test_cases.count(),
                    feedback=self._generate_feedback(status),
                    submitted_at=timezone.now() - timezone.timedelta(days=random.randint(0, 365))
                )
                
                created_submissions.append(submission)
                
                if (i + 1) % 1000 == 0:
                    print(f"      Progress: {i + 1}/{count} submissions...")
        
        # Update user stats
        print("   -> Updating user statistics...")
        for user in self.users:
            user.total_problems_solved = user_solved_count[user.id]
            user.save(update_fields=['total_problems_solved'])
        
        print(f"   ✓ Created {len(created_submissions)} submissions")
        
        # Statistics
        status_counts = {}
        for sub in created_submissions:
            status_counts[sub.status] = status_counts.get(sub.status, 0) + 1
        
        print("   📊 Submission statistics:")
        for status, count in sorted(status_counts.items()):
            percentage = (count / len(created_submissions)) * 100
            print(f"      - {status}: {count} ({percentage:.1f}%)")
        
        return created_submissions
    
    def _generate_fake_code(self, language_code):
        """Tạo code giả"""
        if language_code == 'python':
            return """def solve():
    n = int(input())
    arr = list(map(int, input().split()))
    result = sum(arr)
    print(result)

if __name__ == '__main__':
    solve()
"""
        elif language_code == 'java':
            return """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int result = 0;
        for (int i = 0; i < n; i++) {
            result += sc.nextInt();
        }
        System.out.println(result);
    }
}
"""
        else:
            return """#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    int result = 0;
    for (int i = 0; i < n; i++) {
        int x;
        cin >> x;
        result += x;
    }
    cout << result << endl;
    return 0;
}
"""
    
    def _generate_feedback(self, status):
        """Tạo feedback message"""
        if status == 'ac':
            return "All test cases passed!"
        elif status == 'wa':
            return "Wrong answer on test case " + str(random.randint(3, 10))
        elif status == 'tle':
            return "Time limit exceeded on test case " + str(random.randint(5, 12))
        elif status == 'mle':
            return "Memory limit exceeded"
        elif status == 're':
            return "Runtime error: " + random.choice(['IndexError', 'ValueError', 'ZeroDivisionError'])
        elif status == 'ce':
            return "Compilation error: syntax error"
        return "Unknown error"


class Command(BaseCommand):
    help = 'Tạo fake data để test recommendation system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--problems',
            type=int,
            default=200,
            help='Số lượng problems cần tạo',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=100,
            help='Số lượng users cần tạo',
        )
        parser.add_argument(
            '--submissions',
            type=int,
            default=10000,
            help='Số lượng submissions cần tạo',
        )
        parser.add_argument(
            '--skip-sync',
            action='store_true',
            help='Không sync problems với DOMjudge',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Xóa toàn bộ dữ liệu cũ trước khi tạo mới (CẢNH BÁO: Mất hết data!)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('     FAKE DATA GENERATOR FOR RECOMMENDATION SYSTEM'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        start_time = time.time()
        
        # Confirm if clear existing
        if options['clear_existing']:
            self.stdout.write(self.style.WARNING('\n⚠️  WARNING: This will DELETE ALL existing data!'))
            confirm = input('Type "yes" to continue: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
            
            self.stdout.write('[0/4] Clearing existing data...')
            Submissions.objects.all().delete()
            TagProblem.objects.all().delete()
            TestCase.objects.all().delete()
            Problem.objects.all().delete()
            User.objects.exclude(username='admin').delete()
            self.stdout.write(self.style.SUCCESS('   ✓ Cleared'))
        
        # Initialize faker
        faker = DataFaker()
        faker.setup_prerequisites()
        
        # Generate data
        try:
            faker.generate_users(options['users'])
            faker.generate_problems(
                options['problems'], 
                sync_to_domjudge=not options['skip_sync']
            )
            faker.generate_submissions(options['submissions'])
            
            # Summary
            elapsed = time.time() - start_time
            
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('     FAKE DATA GENERATION COMPLETED'))
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write(f'\n📊 Summary:')
            self.stdout.write(f'   - Users created: {len(faker.users)}')
            self.stdout.write(f'   - Problems created: {len(faker.problems)}')
            self.stdout.write(f'   - Problems synced to DOMjudge: {Problem.objects.filter(is_synced_to_domjudge=True).count()}')
            self.stdout.write(f'   - Total submissions: {Submissions.objects.count()}')
            self.stdout.write(f'   - Time elapsed: {elapsed:.2f}s')
            
            self.stdout.write(self.style.SUCCESS('\n✅ Done! You can now run: python manage.py train_recommendation\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {str(e)}'))
            import traceback
            traceback.print_exc()
