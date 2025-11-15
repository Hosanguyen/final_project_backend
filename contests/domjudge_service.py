import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
import json
from io import BytesIO
from datetime import timedelta


class DOMjudgeContestService:
    """Service to interact with DOMjudge Contest API"""
    
    def __init__(self):
        self.api_url = getattr(settings, 'DOMJUDGE_API_URL', 'http://localhost:8088/api/v4')
        self.username = getattr(settings, 'DOMJUDGE_USERNAME', 'admin')
        self.password = getattr(settings, 'DOMJUDGE_PASSWORD', 'admin')
    
    def create_contest(self, contest_data):
        """
        Create a contest in DOMjudge
        
        Args:
            contest_data: dict containing contest information
                - id: contest slug/id
                - name: contest name
                - formal_name: formal contest name
                - start_time: ISO 8601 datetime string
                - duration: duration string (e.g., "5:00:00")
                - scoreboard_freeze_duration: freeze duration string (optional)
                - penalty_time: penalty time in minutes
        
        Returns:
            contest_id: string - ID of created contest
        """
        url = f"{self.api_url}/contests"
        
        # Convert contest data to JSON format expected by DOMjudge
        domjudge_data = {
            "id": contest_data.get('id'),
            "name": contest_data.get('name'),
            "formal_name": contest_data.get('formal_name', contest_data.get('name')),
            "start_time": contest_data.get('start_time'),
            "duration": contest_data.get('duration'),
            "penalty_time": contest_data.get('penalty_time', 20)
        }
        
        # Add optional fields
        if contest_data.get('scoreboard_freeze_duration'):
            domjudge_data['scoreboard_freeze_duration'] = contest_data.get('scoreboard_freeze_duration')
        
        # Convert to JSON file for multipart upload
        json_content = json.dumps(domjudge_data, indent=2)
        json_file = BytesIO(json_content.encode('utf-8'))
        
        files = {
            'json': ('contest.json', json_file, 'application/json')
        }
        
        try:
            response = requests.post(
                url,
                files=files,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                contest_id = response.text.strip().strip('"')  # Remove quotes if present
                return contest_id
            else:
                error_message = response.text
                raise Exception(f"DOMjudge API error ({response.status_code}): {error_message}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create contest in DOMjudge: {str(e)}")
    
    def get_contest(self, contest_id):
        """Get contest details from DOMjudge"""
        url = f"{self.api_url}/contests/{contest_id}"
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get contest: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get contest from DOMjudge: {str(e)}")
    
    def update_contest(self, contest_id, contest_data):
        """Update contest in DOMjudge"""
        url = f"{self.api_url}/contests/{contest_id}"
        
        # Convert to JSON file for multipart upload
        json_content = json.dumps(contest_data, indent=2)
        json_file = BytesIO(json_content.encode('utf-8'))
        
        files = {
            'json': ('contest.json', json_file, 'application/json')
        }
        
        try:
            response = requests.put(
                url,
                files=files,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to update contest: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to update contest in DOMjudge: {str(e)}")
    
    def delete_contest(self, contest_id):
        """Delete contest from DOMjudge"""
        url = f"{self.api_url}/contests/{contest_id}"
        
        try:
            response = requests.delete(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                return True
            else:
                raise Exception(f"Failed to delete contest: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete contest from DOMjudge: {str(e)}")
    
    def list_contests(self):
        """List all contests from DOMjudge"""
        url = f"{self.api_url}/contests"
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list contests: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to list contests from DOMjudge: {str(e)}")
    
    def add_problem_to_contest(self, contest_id, problem_id, problem_data):
        """
        Add a problem to a contest in DOMjudge
        
        Args:
            contest_id: string - contest slug/id
            problem_id: string - problem slug/id
            problem_data: dict containing:
                - label: string (required) - problem label (A, B, C, etc.)
                - color: string (optional) - color name
                - rgb: string (optional) - RGB color code
                - points: int (optional) - points for the problem
                - lazy_eval_results: int (optional) - 0 or 1
        
        Returns:
            dict - DOMjudge response with problem details
        """
        url = f"{self.api_url}/contests/{contest_id}/problems/{problem_id}"
        
        try:
            response = requests.put(
                url,
                json=problem_data,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to add problem to contest: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to add problem to contest in DOMjudge: {str(e)}")
    
    def remove_problem_from_contest(self, contest_id, problem_id):
        """
        Remove a problem from a contest in DOMjudge
        
        Args:
            contest_id: string - contest slug/id
            problem_id: string - problem slug/id
        
        Returns:
            bool - True if successful
        """
        url = f"{self.api_url}/contests/{contest_id}/problems/{problem_id}"
        
        try:
            response = requests.delete(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                return True
            else:
                raise Exception(f"Failed to remove problem from contest: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to remove problem from contest in DOMjudge: {str(e)}")
