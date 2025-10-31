from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from .models import Contest, ContestProblem
from .serializers import (
    ContestCreateSerializer,
    ContestSerializer,
    ContestListSerializer
)
from .domjudge_service import DOMjudgeContestService
from common.authentication import CustomJWTAuthentication


class ContestCreateView(APIView):
    """Create a new contest and sync with DOMjudge"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ContestCreateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create contest in database
            contest = serializer.save()
            
            # Prepare data for DOMjudge
            duration = contest.end_at - contest.start_at
            duration_str = self._format_duration(duration)
            
            # Calculate freeze duration if freeze_rankings_at is set
            freeze_duration_str = None
            if contest.freeze_rankings_at:
                freeze_duration = contest.end_at - contest.freeze_rankings_at
                freeze_duration_str = self._format_duration(freeze_duration)
            
            domjudge_data = {
                'id': contest.slug,
                'name': contest.title,
                'formal_name': contest.title,
                'start_time': contest.start_at.isoformat(),
                'duration': duration_str,
                'penalty_time': contest.penalty_time
            }
            
            if freeze_duration_str:
                domjudge_data['scoreboard_freeze_duration'] = freeze_duration_str
            
            # Create contest in DOMjudge
            domjudge_service = DOMjudgeContestService()
            domjudge_contest_id = domjudge_service.create_contest(domjudge_data)
            
            # Return response
            response_serializer = ContestSerializer(contest)
            return Response({
                'message': 'Contest created successfully',
                'contest': response_serializer.data,
                'domjudge_contest_id': domjudge_contest_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # If DOMjudge creation fails, delete the contest from database
            if 'contest' in locals():
                contest.delete()
            
            return Response({
                'error': 'Failed to create contest',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _format_duration(self, duration):
        """Format timedelta to HH:MM:SS string"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"


class ContestListView(APIView):
    """List all contests"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        contests = Contest.objects.all()
        
        # Filter by status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            now = timezone.now()
            if status_filter == 'upcoming':
                contests = contests.filter(start_at__gt=now)
            elif status_filter == 'running':
                contests = contests.filter(start_at__lte=now, end_at__gte=now)
            elif status_filter == 'finished':
                contests = contests.filter(end_at__lt=now)
        
        # Filter by visibility
        visibility_filter = request.query_params.get('visibility', None)
        if visibility_filter:
            contests = contests.filter(visibility=visibility_filter)
        
        serializer = ContestListSerializer(contests, many=True)
        return Response({
            'contests': serializer.data,
            'total': contests.count()
        }, status=status.HTTP_200_OK)


class ContestDetailView(APIView):
    """Get, update, or delete a specific contest"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            serializer = ContestSerializer(contest)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            serializer = ContestCreateSerializer(contest, data=request.data, partial=True, context={'request': request})
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            contest = serializer.save(updated_by=request.user)
            response_serializer = ContestSerializer(contest)
            
            return Response({
                'message': 'Contest updated successfully',
                'contest': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, contest_id):
        try:
            contest = Contest.objects.get(id=contest_id)
            
            # Try to delete from DOMjudge
            try:
                domjudge_service = DOMjudgeContestService()
                domjudge_service.delete_contest(contest.slug)
            except Exception as e:
                # Log error but continue with local deletion
                print(f"Failed to delete from DOMjudge: {str(e)}")
            
            contest.delete()
            
            return Response({
                'message': 'Contest deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Contest.DoesNotExist:
            return Response({
                'error': 'Contest not found'
            }, status=status.HTTP_404_NOT_FOUND)
