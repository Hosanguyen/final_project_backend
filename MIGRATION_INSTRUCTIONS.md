# Generated migration for ContestRanking model
# This file needs to be created by running: python manage.py makemigrations

# After the implementation is complete, run these commands in order:

# 1. Create the migration file
python manage.py makemigrations contests

# 2. Apply the migration to the database
python manage.py migrate contests

# 3. (Optional) Recalculate rankings for existing contests
# You can create a management command or run this in Django shell:
from contests.ranking_service import ContestRankingService
from contests.models import Contest

# For each contest, recalculate all rankings
for contest in Contest.objects.all():
    count = ContestRankingService.recalculate_all_rankings(contest.id)
    print(f"Updated {count} rankings for contest: {contest.title}")
