"""
Scheduled Tasks for Django-Q
"""
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def train_recommendation_model():
    """
    Task tự động train recommendation model và update ratings
    Chạy hàng ngày vào lúc 2:00 AM
    """
    try:
        logger.info("[Scheduled Task] Starting recommendation model training...")
        
        # Gọi management command với flag update-ratings
        call_command('train_recommendation', '--update-ratings')
        
        logger.info("[Scheduled Task] Training completed successfully!")
        return "Training completed"
        
    except Exception as e:
        logger.error(f"[Scheduled Task] Training failed: {str(e)}")
        raise


def train_recommendation_model_no_update():
    """
    Task train model nhưng không update ratings
    Có thể dùng cho việc train nhanh trong ngày
    """
    try:
        logger.info("[Scheduled Task] Starting recommendation model training (no rating update)...")
        call_command('train_recommendation')
        logger.info("[Scheduled Task] Training completed!")
        return "Training completed without rating update"
    except Exception as e:
        logger.error(f"[Scheduled Task] Training failed: {str(e)}")
        raise
