"""
Service for calculating and updating contest rankings
"""
from django.db.models import Q, Count, Sum, Max, Min, F
from django.utils import timezone
from decimal import Decimal
from .models import Contest, ContestParticipant, ContestProblem
from problems.models import Submissions


class ContestRankingService:
    """Service to calculate and update contest rankings"""
    
    @staticmethod
    def update_user_ranking(contest_id, user_id):
        """
        Update ranking for a specific user in a contest
        Called after each submission
        """
        from contests.models import Contest, ContestParticipant
        from users.models import User
        
        try:
            contest = Contest.objects.get(id=contest_id)
            user = User.objects.get(id=user_id)
            
            # Get or create participant
            participant, _ = ContestParticipant.objects.get_or_create(
                contest=contest,
                user=user,
                defaults={'is_active': True}
            )
            
        except (Contest.DoesNotExist, User.DoesNotExist):
            return None
        
        if contest.slug == 'practice':
            # Practice mode: only count solved problems
            ContestRankingService._calculate_practice_ranking(participant, contest, user)
        elif contest.contest_mode == 'ICPC':
            # ICPC mode: count solved + penalty time
            ContestRankingService._calculate_icpc_ranking(participant, contest, user)
        elif contest.contest_mode == 'OI':
            # OI mode: sum scores from all problems
            ContestRankingService._calculate_oi_ranking(participant, contest, user)
        
        participant.save()
        return participant
    
    @staticmethod
    def _calculate_practice_ranking(participant, contest, user):
        """
        Calculate ranking for practice contest
        Only count number of solved problems
        """
        # Get all AC submissions for this user in this contest
        ac_submissions = Submissions.objects.filter(
            contest=contest,
            user=user,
            status__in=['AC', 'correct', 'Correct'],
            submitted_at__gte=contest.start_at,
            submitted_at__lte=contest.end_at
        ).values('problem').distinct()
        
        solved_count = ac_submissions.count()
        
        # Get last submission time
        last_submission = Submissions.objects.filter(
            contest=contest,
            user=user,
            submitted_at__gte=contest.start_at,
            submitted_at__lte=contest.end_at
        ).order_by('-submitted_at').first()
        
        participant.solved_count = solved_count
        participant.total_score = Decimal(solved_count)  # Score = number of solved problems
        participant.penalty_seconds = 0  # No penalty in practice mode
        participant.last_submission_at = last_submission.submitted_at if last_submission else None
    
    @staticmethod
    def _calculate_icpc_ranking(participant, contest, user):
        """
        Calculate ranking for ICPC mode contest
        
        Rules:
        1. Each solved problem = 1 point
        2. Penalty = time to AC + (wrong submissions * penalty_time)
        3. Time is calculated from contest start to first AC
        4. Only AC problems contribute to penalty
        5. During freeze: submissions after freeze_rankings_at are excluded from ranking
        6. After contest ends: all submissions are counted
        """
        from django.utils import timezone
        
        contest_problems = ContestProblem.objects.filter(contest=contest)
        
        solved_count = 0
        total_penalty_minutes = 0
        last_submission_time = None
        
        # Determine if we should apply freeze
        # Only apply freeze if contest is still running and freeze_time exists
        now = timezone.now()
        freeze_time = contest.freeze_rankings_at
        should_apply_freeze = freeze_time and now < contest.end_at
        
        for contest_problem in contest_problems:
            # Get all submissions for this problem by this user
            submissions = Submissions.objects.filter(
                contest=contest,
                user=user,
                problem=contest_problem.problem,
                submitted_at__gte=contest.start_at,
                submitted_at__lte=contest.end_at
            ).order_by('submitted_at')
            
            if not submissions.exists():
                continue
            
            # Separate frozen and unfrozen submissions only if freeze is active
            if should_apply_freeze:
                unfrozen_submissions = submissions.filter(submitted_at__lt=freeze_time)
            else:
                # After contest ends, count all submissions
                unfrozen_submissions = submissions
            
            # Find first AC submission (in unfrozen period during freeze, all submissions after contest)
            first_ac = unfrozen_submissions.filter(
                status__in=['AC', 'correct', 'Correct']
            ).first()
            
            if first_ac:
                solved_count += 1
                
                # Calculate time from contest start to AC (in minutes)
                time_to_ac = (first_ac.submitted_at - contest.start_at).total_seconds() / 60
                
                # Count wrong submissions before first AC (only unfrozen during freeze, all after contest)
                wrong_count = unfrozen_submissions.filter(
                    submitted_at__lt=first_ac.submitted_at
                ).exclude(
                    status__in=['AC', 'correct', 'Correct']
                ).count()
                
                # Calculate penalty for this problem
                problem_penalty = time_to_ac + (wrong_count * contest.penalty_time)
                total_penalty_minutes += problem_penalty
            
            # Track last submission (only unfrozen during freeze, all after contest)
            last_sub = unfrozen_submissions.last() if should_apply_freeze else submissions.last()
            if last_sub and (not last_submission_time or last_sub.submitted_at > last_submission_time):
                last_submission_time = last_sub.submitted_at
        
        participant.solved_count = solved_count
        participant.total_score = Decimal(solved_count)
        participant.penalty_seconds = int(total_penalty_minutes * 60)  # Convert to seconds
        participant.last_submission_at = last_submission_time
    
    @staticmethod
    def _calculate_oi_ranking(participant, contest, user):
        """
        Calculate ranking for OI mode contest
        
        Rules:
        1. Each problem has max points (usually 100)
        2. Score = sum of (tests_passed / total_tests) * max_points for each problem
        3. Take best submission for each problem
        """
        contest_problems = ContestProblem.objects.filter(contest=contest)
        
        total_score = Decimal(0)
        solved_count = 0  # Count problems with 100% score
        last_submission_time = None
        
        for contest_problem in contest_problems:
            # Get all submissions for this problem by this user
            submissions = Submissions.objects.filter(
                contest=contest,
                user=user,
                problem=contest_problem.problem,
                submitted_at__gte=contest.start_at,
                submitted_at__lte=contest.end_at
            ).order_by('submitted_at')

            if not submissions.exists():
                continue

            # Recompute score from test_passed/test_total and choose the best
            max_points = Decimal(contest_problem.point or 100)
            best_score_for_problem = Decimal(0)

            for sub in submissions:
                # Track last submission time while iterating
                if not last_submission_time or sub.submitted_at > last_submission_time:
                    last_submission_time = sub.submitted_at

                tp = getattr(sub, 'test_passed', None)
                tt = getattr(sub, 'test_total', None)

                if tp is None or tt in (None, 0):
                    continue

                # Compute fractional score and clamp within [0, max_points]
                try:
                    frac = Decimal(tp) / Decimal(tt)
                except Exception:
                    continue

                computed = (frac * max_points)
                if computed > best_score_for_problem:
                    best_score_for_problem = computed

            # Accumulate the best score for this problem
            total_score += best_score_for_problem

            # Count as solved if achieved full points for the problem
            if best_score_for_problem >= max_points:
                solved_count += 1
        
        participant.solved_count = solved_count
        participant.total_score = total_score
        participant.penalty_seconds = 0  # No penalty in OI mode, use last_submission_at for tiebreaker
        participant.last_submission_at = last_submission_time
    
    @staticmethod
    def get_contest_leaderboard(contest_id):
        """
        Get full leaderboard for a contest
        Returns list of participants with ranking info
        """
        from contests.models import Contest, ContestParticipant
        
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return []
        
        # Get all active participants for this contest
        if contest.slug == 'practice':
            # Practice: order by solved_count desc, submissions asc, then name asc
            participants = ContestParticipant.objects.filter(
                contest=contest,
                is_active=True
            ).select_related('user', 'contest').annotate(
                submissions_count=Count(
                    'user__submissions__problem',
                    filter=(
                        Q(user__submissions__contest=contest) &
                        Q(user__submissions__submitted_at__gte=contest.start_at) &
                        Q(user__submissions__submitted_at__lte=contest.end_at)
                    ),
                    distinct=True
                )
            ).order_by(
                '-solved_count',
                'submissions_count',
                'user__full_name',
                'user__username'
            )
        elif contest.contest_mode == 'ICPC':
            # ICPC: order by solved_count desc, penalty_seconds asc, last_submission_at asc
            participants = ContestParticipant.objects.filter(
                contest=contest,
                is_active=True
            ).select_related('user', 'contest').order_by(
                '-solved_count',
                'penalty_seconds',
                'last_submission_at'
            )
        elif contest.contest_mode == 'OI':
            # OI: order by total_score desc, last_submission_at asc
            participants = ContestParticipant.objects.filter(
                contest=contest,
                is_active=True
            ).select_related('user', 'contest').order_by(
                '-total_score',
                'last_submission_at'
            )
            for participant in participants:
                ContestRankingService.update_user_ranking(contest_id, participant.user.id)
        else:
            participants = ContestParticipant.objects.filter(
                contest=contest,
                is_active=True
            ).select_related('user', 'contest').order_by(
                '-solved_count',
                'penalty_seconds'
            )
        
        return participants
    
    @staticmethod
    def get_user_problem_details(contest_id, user_id):
        """
        Get detailed submission info for each problem in the contest for a user
        Used for ICPC leaderboard display
        
        Returns dict: {
            problem_id: {
                'status': 'AC'/'WA'/'pending'/None,
                'attempts': number of submissions (unfrozen only during freeze, all after contest),
                'frozen_attempts': number of submissions during freeze (0 after contest ends),
                'time_minutes': time to AC in minutes (from contest start),
                'penalty': penalty time for this problem
            }
        }
        """
        from contests.models import Contest, ContestProblem
        from django.utils import timezone
        
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return {}
        
        contest_problems = ContestProblem.objects.filter(contest=contest).order_by('label')
        problem_details = {}
        
        # Determine if we should apply freeze
        now = timezone.now()
        freeze_time = contest.freeze_rankings_at
        should_apply_freeze = freeze_time and now < contest.end_at
        
        for contest_problem in contest_problems:
            submissions = Submissions.objects.filter(
                contest=contest,
                user_id=user_id,
                problem=contest_problem.problem,
                submitted_at__gte=contest.start_at,
                submitted_at__lte=contest.end_at
            ).order_by('submitted_at')
            
            if not submissions.exists():
                problem_details[contest_problem.problem.id] = {
                    'problem_label': contest_problem.label,
                    'status': None,
                    'attempts': 0,
                    'frozen_attempts': 0,
                    'time_minutes': None,
                    'penalty': 0,
                    'score': None,
                    'test_passed': None,
                    'test_total': None
                }
                continue
            
            # Separate frozen and unfrozen submissions only if freeze is active
            if should_apply_freeze:
                unfrozen_submissions = submissions.filter(submitted_at__lt=freeze_time)
                frozen_submissions = submissions.filter(submitted_at__gte=freeze_time)
                frozen_count = frozen_submissions.count()
            else:
                # After contest ends, all submissions are unfrozen
                unfrozen_submissions = submissions
                frozen_count = 0
            
            # Find first AC (in unfrozen period during freeze, all submissions after contest)
            first_ac = unfrozen_submissions.filter(
                status__in=['AC', 'correct', 'Correct']
            ).first()
            
            unfrozen_count = unfrozen_submissions.count()
            
            if first_ac:
                # Calculate time to AC
                time_to_ac_minutes = int((first_ac.submitted_at - contest.start_at).total_seconds() / 60)
                
                # Count wrong submissions before AC
                wrong_before_ac = unfrozen_submissions.filter(
                    submitted_at__lt=first_ac.submitted_at
                ).exclude(
                    status__in=['AC', 'correct', 'Correct']
                ).count()
                
                problem_details[contest_problem.problem.id] = {
                    'problem_label': contest_problem.label,
                    'status': 'AC',
                    'attempts': unfrozen_count,
                    'frozen_attempts': frozen_count,
                    'wrong_attempts': wrong_before_ac,
                    'time_minutes': time_to_ac_minutes,
                    'penalty': time_to_ac_minutes + (wrong_before_ac * contest.penalty_time),
                    'score': first_ac.score,
                    'test_passed': first_ac.test_passed,
                    'test_total': first_ac.test_total
                }
            else:
                # No AC in unfrozen period
                has_wrong = unfrozen_submissions.exclude(
                    status__in=['AC', 'correct', 'Correct']
                ).exists()
                
                last_submission = submissions.last()
                
                problem_details[contest_problem.problem.id] = {
                    'problem_label': contest_problem.label,
                    'status': 'WA' if has_wrong else 'pending',
                    'attempts': unfrozen_count,
                    'frozen_attempts': frozen_count,
                    'wrong_attempts': unfrozen_count,
                    'time_minutes': None,
                    'penalty': 0,
                    'score': last_submission.score if contest.contest_mode == 'OI' else None,
                    'test_passed': last_submission.test_passed,
                    'test_total': last_submission.test_total
                }
        
        return problem_details
    
    @staticmethod
    def recalculate_all_rankings(contest_id):
        """
        Recalculate rankings for all participants in a contest
        Useful for manual recalculation or fixing inconsistencies
        """
        from contests.models import Contest, ContestParticipant
        
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return 0
        
        # Get all active participants
        participants = ContestParticipant.objects.filter(
            contest=contest,
            is_active=True
        )
        
        count = 0
        for participant in participants:
            ContestRankingService.update_user_ranking(contest_id, participant.user.id)
            count += 1
        
        return count
