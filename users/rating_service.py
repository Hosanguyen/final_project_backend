"""
Service tính rating cho user sau mỗi contest
Sử dụng thuật toán Elo cải tiến giống Codeforces
"""
import math
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


class RatingService:
    """Service để tính toán và cập nhật rating"""
    
    @staticmethod
    def calculate_expected_rank(user_rating, all_ratings):
        """
        Tính expected rank của user dựa trên rating
        Sử dụng công thức Elo
        
        Args:
            user_rating: Rating của user
            all_ratings: List rating của tất cả participants
            
        Returns:
            Expected rank (float)
        """
        expected_rank = 1.0
        for other_rating in all_ratings:
            if other_rating != user_rating:
                expected_rank += 1.0 / (1.0 + math.pow(10, (user_rating - other_rating) / 400.0))
        return expected_rank
    
    @staticmethod
    def calculate_rating_change(old_rating, actual_rank, expected_rank, contests_participated, volatility):
        """
        Tính rating change dựa trên performance
        
        Args:
            old_rating: Rating cũ
            actual_rank: Thứ hạng thực tế
            expected_rank: Thứ hạng dự đoán
            contests_participated: Số contest đã tham gia
            volatility: Độ biến động rating
            
        Returns:
            new_rating, rating_change
        """
        # K-factor: càng thi nhiều càng giảm (ổn định hơn)
        # Newbie: K = 100-200, Experienced: K = 32-64
        if contests_participated <= 5:
            k_factor = 200
        elif contests_participated <= 10:
            k_factor = 100
        elif contests_participated <= 20:
            k_factor = 64
        else:
            k_factor = 32
        
        # Điều chỉnh K-factor theo volatility
        k_factor = k_factor * (volatility / 350.0)
        
        # Tính rating change
        # Nếu rank thực tế tốt hơn expected (actual < expected) => tăng rating
        # Nếu rank thực tế tệ hơn expected (actual > expected) => giảm rating
        rating_change = int(k_factor * (expected_rank - actual_rank) / expected_rank)
        
        # Giới hạn rating change
        rating_change = max(-300, min(300, rating_change))
        
        new_rating = old_rating + rating_change
        
        # Rating không thể âm
        new_rating = max(0, new_rating)
        
        return new_rating, rating_change
    
    @staticmethod
    def update_volatility(old_volatility, rating_change):
        """
        Update volatility dựa trên rating change
        Rating thay đổi nhiều => volatility cao
        """
        # Tăng volatility nếu rating thay đổi nhiều
        volatility_change = abs(rating_change) * 0.5
        new_volatility = old_volatility + volatility_change
        
        # Decay về 350 theo thời gian
        new_volatility = new_volatility * 0.95 + 350 * 0.05
        
        # Giới hạn volatility
        new_volatility = max(50, min(500, new_volatility))
        
        return new_volatility
    
    @staticmethod
    @transaction.atomic
    def update_contest_ratings(contest_id):
        """
        Update rating cho tất cả participants sau khi contest kết thúc
        
        Args:
            contest_id: ID của contest
            
        Returns:
            Number of participants updated
        """
        from contests.models import Contest, ContestParticipant
        from users.models import User, ContestRatingChange
        
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return 0
        
        # Chỉ tính rating cho contest rated (không phải practice)
        if contest.slug == 'practice':
            return 0
        
        # Kiểm tra xem contest này đã được tính rating chưa
        existing_changes = ContestRatingChange.objects.filter(contest=contest)
        if existing_changes.exists():
            # Nếu đã tính rồi, rollback rating về trạng thái trước đó
            for change in existing_changes:
                user = change.user
                # Trừ đi rating change cũ
                user.current_rating = change.old_rating
                # Giảm contests_participated
                user.contests_participated = max(0, user.contests_participated - 1)
                # Nếu đã thắng contest này trước đó thì trừ đi
                if change.rank == 1:
                    user.contests_won = max(0, user.contests_won - 1)
                # Update rank
                user.update_rank()
                user.save()
            
            # Xóa các records rating change cũ
            existing_changes.delete()
        
        # Lấy danh sách participants với ranking
        participants = ContestParticipant.objects.filter(
            contest=contest,
            is_active=True
        ).select_related('user').order_by(
            '-solved_count',
            'penalty_seconds',
            'last_submission_at'
        )
        
        if participants.count() < 2:
            # Cần ít nhất 2 người để tính rating
            return 0
        
        # Lấy rating của tất cả participants (từ User model)
        participant_data = []
        for rank, participant in enumerate(participants, start=1):
            user = participant.user
            participant_data.append({
                'participant': participant,
                'user': user,
                'actual_rank': rank,
                'old_rating': user.current_rating,
            })
        
        # Lấy list tất cả ratings để tính expected rank
        all_ratings = [data['old_rating'] for data in participant_data]
        
        # Tính rating change cho từng participant
        updated_count = 0
        for data in participant_data:
            user = data['user']
            old_rating = data['old_rating']
            actual_rank = data['actual_rank']
            
            # Tính expected rank
            expected_rank = RatingService.calculate_expected_rank(old_rating, all_ratings)
            
            # Tính new rating
            new_rating, rating_change = RatingService.calculate_rating_change(
                old_rating=old_rating,
                actual_rank=actual_rank,
                expected_rank=expected_rank,
                contests_participated=user.contests_participated,
                volatility=user.rating_volatility
            )
            
            # Update volatility
            new_volatility = RatingService.update_volatility(
                user.rating_volatility,
                rating_change
            )
            
            # Update User rating fields
            user.current_rating = new_rating
            user.max_rating = max(user.max_rating, new_rating)
            user.contests_participated += 1
            user.rating_volatility = new_volatility
            user.last_contest_at = timezone.now()
            
            # Update rank
            user.update_rank()
            
            # Check if won contest
            if actual_rank == 1:
                user.contests_won += 1
            
            # Update total problems solved from all practice submissions
            from problems.models import Submissions
            total_solved = Submissions.objects.filter(
                user=user,
                status__in=['AC', 'correct', 'Correct']
            ).values('problem').distinct().count()
            user.total_problems_solved = total_solved
            
            user.save()
            
            # Create rating change record
            ContestRatingChange.objects.create(
                user=user,
                contest=contest,
                old_rating=old_rating,
                new_rating=new_rating,
                rating_change=rating_change,
                rank=actual_rank,
                solved_count=data['participant'].solved_count
            )
            
            updated_count += 1
        
        return updated_count
    
    @staticmethod
    def get_global_leaderboard(limit=100, offset=0):
        """
        Lấy bảng xếp hạng global
        
        Args:
            limit: Số lượng user trả về
            offset: Vị trí bắt đầu
            
        Returns:
            QuerySet of User
        """
        from users.models import User
        
        return User.objects.order_by(
            '-current_rating',
            '-max_rating',
            'username'
        )[offset:offset + limit]
    
    @staticmethod
    def get_user_rating_info(user_id):
        """
        Lấy thông tin rating của user
        
        Args:
            user_id: ID của user
            
        Returns:
            User object hoặc None
        """
        from users.models import User
        
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_rating_history(user_id, limit=50):
        """
        Lấy lịch sử rating changes của user
        
        Args:
            user_id: ID của user
            limit: Số lượng records trả về
            
        Returns:
            QuerySet of ContestRatingChange
        """
        from users.models import ContestRatingChange
        
        return ContestRatingChange.objects.filter(
            user_id=user_id
        ).select_related('contest').order_by('-created_at')[:limit]
