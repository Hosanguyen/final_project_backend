"""
Django Management Command: Train Recommendation Model
Lấy dữ liệu thực từ Database để train model gợi ý bài toán cho users.

Usage: python manage.py train_recommendation
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
import pandas as pd
import time

from problems.models import Problem, Submissions, TagProblem
from course.models import Tag
from users.models import User
from common.recommender import ProductionRecommender


class Command(BaseCommand):
    help = 'Train recommendation model từ dữ liệu thực trong database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-ratings',
            action='store_true',
            help='Cập nhật ratings bài toán trước khi train (dựa trên user đã giải)',
        )
        parser.add_argument(
            '--model-name',
            type=str,
            default='recommendation_model.pkl',
            help='Tên file model để lưu',
        )
        parser.add_argument(
            '--min-submissions',
            type=int,
            default=5,
            help='Số lượng AC submissions tối thiểu để tính rating bài toán',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('     RECOMMENDATION MODEL TRAINING'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        start_time = time.time()
        
        # ============ BƯỚC 1: LOAD DATA TỪ DATABASE ============
        self.stdout.write('[1/4] Loading data from database...')
        
        # Load Problems
        problems_qs = Problem.objects.filter(
            is_public=True,
        ).prefetch_related('tags')
        
        problems_data = []
        for prob in problems_qs:
            tags_list = [tag.slug or tag.name.lower() for tag in prob.tags.all()]
            problems_data.append({
                'problem_id': prob.id,
                'title': prob.title,
                'difficulty': prob.difficulty,
                'rating': prob.rating,
                'tags': tags_list,
                'is_public': prob.is_public,
                'is_synced': prob.is_synced_to_domjudge
            })
        
        df_problems = pd.DataFrame(problems_data)
        
        if df_problems.empty:
            self.stdout.write(self.style.ERROR('   ✗ Không có bài toán public nào!'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Loaded {len(df_problems)} problems'))
        
        # Load Submissions (chỉ lấy AC trong practice mode)
        submissions_qs = Submissions.objects.filter(
            status='ac',
            contest__isnull=True  # Practice mode only
        ).select_related('user', 'problem')
        
        submissions_data = []
        for sub in submissions_qs:
            submissions_data.append({
                'user_id': sub.user_id,
                'problem_id': sub.problem_id,
                'status': sub.status,
                'user_rating': sub.user.current_rating if sub.user else 1500
            })
        
        df_submissions = pd.DataFrame(submissions_data)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Loaded {len(df_submissions)} AC submissions'))
        
        # Statistics
        if not df_submissions.empty:
            unique_users = df_submissions['user_id'].nunique()
            unique_problems = df_submissions['problem_id'].nunique()
            self.stdout.write(f'      - Unique users: {unique_users}')
            self.stdout.write(f'      - Problems with AC: {unique_problems}')
        
        # ============ BƯỚC 2: UPDATE RATINGS (Optional) ============
        if options['update_ratings'] and not df_submissions.empty:
            self.stdout.write('\n[2/4] Updating problem ratings...')
            
            recommender = ProductionRecommender(model_path=options['model_name'])
            df_problems = recommender.recalculate_problem_ratings(df_problems, df_submissions)
            
            # Lưu rating mới vào database
            self.stdout.write('   -> Saving new ratings to database...')
            updated_count = 0
            for _, row in df_problems.iterrows():
                Problem.objects.filter(id=row['problem_id']).update(
                    rating=row['rating'],
                    difficulty=row['difficulty']
                )
                updated_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'   ✓ Updated {updated_count} problems in database'))
        else:
            self.stdout.write('\n[2/4] Skipping rating update (use --update-ratings to enable)')
        
        # ============ BƯỚC 3: TRAIN MODEL ============
        self.stdout.write('\n[3/4] Training recommendation model...')
        
        recommender = ProductionRecommender(model_path=options['model_name'])
        train_success = recommender.fit(df_problems, df_submissions)
        
        if not train_success:
            self.stdout.write(self.style.ERROR('   ✗ Training failed!'))
            return
        
        # ============ BƯỚC 4: SAVE MODEL ============
        self.stdout.write('\n[4/4] Saving model...')
        model_path = recommender.save_model()
        
        # ============ SUMMARY ============
        elapsed_time = time.time() - start_time
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('     TRAINING COMPLETED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f'   - Problems: {len(df_problems)}')
        self.stdout.write(f'   - Submissions: {len(df_submissions)}')
        self.stdout.write(f'   - Model saved: {model_path}')
        self.stdout.write(f'   - Training time: {elapsed_time:.2f}s')
        
        # ============ QUICK TEST ============
        if not df_submissions.empty:
            self.stdout.write('\n🧪 Quick Test:')
            
            # Lấy 1 user random có nhiều submissions
            test_user_id = df_submissions['user_id'].value_counts().head(1).index[0]
            test_solved_ids = df_submissions[df_submissions['user_id'] == test_user_id]['problem_id'].tolist()
            
            valid_problem_ids = set(df_problems['problem_id'])
            
            test_recommendations = recommender.recommend(
                user_id=test_user_id,
                solved_ids=test_solved_ids,
                valid_problem_ids_set=valid_problem_ids,
                n_recommendations=5,
                strategy='similar'
            )
            
            self.stdout.write(f'   User {test_user_id} đã giải {len(test_solved_ids)} bài')
            self.stdout.write(f'   Recommendations:')
            for rec in test_recommendations:
                tags_str = ', '.join(rec["tags"]) if rec["tags"] else 'No tags'
                self.stdout.write(f'      - [{rec["problem_id"]}] {rec["title"]} | Rating: {rec["rating"]} | Tags: [{tags_str}] (Score: {rec["score"]:.2f})')
        
        self.stdout.write('\n✅ Done!\n')
