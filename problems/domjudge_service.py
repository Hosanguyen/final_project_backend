import requests
import zipfile
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from course.models import File


class DOMjudgeService:
    def __init__(self):
        self.api_url = getattr(settings, 'DOMJUDGE_API_URL', 'http://localhost:8088/api/v4')
        self.username = getattr(settings, 'DOMJUDGE_USERNAME', 'admin')
        self.password = getattr(settings, 'DOMJUDGE_PASSWORD', 'gFO5CnKMlpVqTlX7')
    
    def sync_problem(self, problem):
        """
        Đồng bộ problem lên DOMjudge
        Returns: domjudge_problem_id (string)
        """
        try:
            # 1. Tạo files từ test cases
            self._create_test_case_files(problem)
            
            # 2. Tạo ZIP package
            zip_file = self._create_problem_package(problem)
            
            # 3. Upload lên DOMjudge
            domjudge_problem_id = self._upload_to_domjudge(problem, zip_file)
            
            return domjudge_problem_id
        
        except Exception as e:
            raise Exception(f"DOMjudge sync failed: {str(e)}")
    
    def _create_test_case_files(self, problem):
        """Tạo input/output files từ text cho mỗi test case"""
        for test_case in problem.test_cases.all():
            # Tạo input file
            if not test_case.input_file:
                input_file = self._create_file_from_text(
                    content=test_case.input_data,
                    filename=f"{problem.slug}_test{test_case.sequence}.in"
                )
                test_case.input_file = input_file
            
            # Tạo output file
            if not test_case.output_file:
                output_file = self._create_file_from_text(
                    content=test_case.output_data,
                    filename=f"{problem.slug}_test{test_case.sequence}.out"
                )
                test_case.output_file = output_file
            
            test_case.save()
    
    def _create_file_from_text(self, content, filename):
        """Tạo File object từ text"""
        file_obj = File()
        file_obj.filename = filename
        file_obj.storage_key.save(
            filename, 
            ContentFile(content.encode('utf-8')), 
            save=False
        )
        file_obj.file_type = 'text/plain'
        file_obj.size = len(content.encode('utf-8'))
        file_obj.save()
        return file_obj
    
    def _create_problem_package(self, problem):
        """Tạo ZIP package theo format DOMjudge"""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add problem.yaml
            problem_yaml = f"""name: '{problem.title}'
timelimit: {problem.time_limit_ms / 1000}
"""
            zip_file.writestr('problem.yaml', problem_yaml)
            
            # Add statement (optional)
            if problem.statement_text:
                zip_file.writestr('problem.pdf', problem.statement_text)  # hoặc HTML
            
            # Add test cases
            sample_count = 1
            secret_count = 1
            
            for test_case in problem.test_cases.order_by('sequence'):
                if test_case.type == 'sample':
                    folder = 'data/sample'
                    file_prefix = f'{sample_count:02d}'
                    sample_count += 1
                else:
                    folder = 'data/secret'
                    file_prefix = f'{secret_count:02d}'
                    secret_count += 1
                
                # Add input file
                with open(test_case.input_file.storage_key.path, 'rb') as f:
                    zip_file.writestr(f'{folder}/{file_prefix}.in', f.read())
                
                # Add output file
                with open(test_case.output_file.storage_key.path, 'rb') as f:
                    zip_file.writestr(f'{folder}/{file_prefix}.ans', f.read())
        
        # Save ZIP as File
        zip_file_obj = File()
        zip_file_obj.filename = f"{problem.slug}.zip"
        zip_file_obj.storage_key.save(
            zip_file_obj.filename,
            ContentFile(zip_buffer.getvalue()),
            save=False
        )
        zip_file_obj.file_type = 'application/zip'
        zip_file_obj.size = zip_buffer.tell()
        zip_file_obj.save()
        
        return zip_file_obj
    
    def _upload_to_domjudge(self, problem, zip_file):
        """Upload problem ZIP lên DOMjudge qua API"""
        
        # Nếu đã có domjudge_problem_id, update thay vì create
        if problem.domjudge_problem_id:
            # Update existing problem
            url = f"{self.api_url}/problems/{problem.domjudge_problem_id}"
            method = 'PUT'
        else:
            # Create new problem
            url = f"{self.api_url}/problems"
            method = 'POST'
        
        with open(zip_file.storage_key.path, 'rb') as f:
            files = {'zip': (zip_file.filename, f, 'application/zip')}
            
            response = requests.request(
                method=method,
                url=url,
                files=files,
                auth=(self.username, self.password)
            )
        
        if response.status_code in [200, 201]:
            data = response.json()
            # DOMjudge trả về problem ID
            return data.get('id') or data.get('externalid') or problem.slug
        else:
            raise Exception(f"DOMjudge API error: {response.status_code} - {response.text}")
    
    def delete_problem(self, domjudge_problem_id):
        """Xóa problem từ DOMjudge"""
        if not domjudge_problem_id:
            return
        
        try:
            response = requests.delete(
                f"{self.api_url}/problems/{domjudge_problem_id}",
                auth=(self.username, self.password)
            )
            
            if response.status_code not in [200, 204]:
                print(f"Failed to delete from DOMjudge: {response.text}")
        
        except Exception as e:
            print(f"Error deleting from DOMjudge: {str(e)}")
    
    def submit_code(self, problem, language, source_code, contest_id=None, team_id=None):
        """
        Submit code đến DOMjudge để chấm
        Returns: submission data (dict with id, language_id, problem_id, etc.)
        """
        # Nếu có contest_id thì submit vào contest, không thì submit trực tiếp
        if contest_id:
            url = f"{self.api_url}/contests/{contest_id}/submissions"
        else:
            url = f"{self.api_url}/submissions"
        
        # Xác định extension dựa trên language code
        extension_map = {
            'c': 'c',
            'cpp': 'cpp',
            'java': 'java',
            'py': 'py',
            'python3': 'py',
            'js': 'js',
            'javascript': 'js'
        }
        extension = extension_map.get(language.code.lower(), language.code)
        filename = f"solution.{extension}"
        
        data = {
            'problem': problem.domjudge_problem_id,
            'language': language.code,
            'team_id': team_id if team_id else 'exteam'
        }
        
        files = {
            'code[]': (filename, source_code.encode('utf-8'), 'text/plain')
        }
        
        response = requests.post(
            url,
            data=data,
            files=files,
            auth=(self.username, self.password)
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Submit failed: {response.status_code} - {response.text}")
    
    def get_submission_result(self, submission_id):
        """Lấy kết quả submission từ DOMjudge"""
        url = f"{self.api_url}/submissions/{submission_id}"
        
        response = requests.get(
            url,
            auth=(self.username, self.password)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Get result failed: {response.status_code}")
    
    def get_judgement(self, submission_id, contest_id=None):
        """
        Lấy judgement (kết quả chấm) từ DOMjudge
        Returns: judgement data with judgement_type_id (AC, WA, TLE, etc.)
        """
        if contest_id:
            url = f"{self.api_url}/contests/{contest_id}/judgements/{submission_id}"
        else:
            url = f"{self.api_url}/judgements/{submission_id}"
        
        response = requests.get(
            url,
            auth=(self.username, self.password)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Nếu chưa có judgement, trả về None
            return None
    
    def get_submissions_by_problem(self, problem_id, contest_id=None):
        """
        Lấy danh sách submissions theo problem từ DOMjudge
        """
        if contest_id:
            url = f"{self.api_url}/contests/{contest_id}/submissions"
        else:
            url = f"{self.api_url}/submissions"
        
        params = {'problem_id': problem_id}
        
        response = requests.get(
            url,
            params=params,
            auth=(self.username, self.password)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Get submissions failed: {response.status_code}")