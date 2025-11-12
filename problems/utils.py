import zipfile
import os
import re
from io import BytesIO
from django.core.files.base import ContentFile
from .models import TestCase
from course.models import File
from django.db import models


class TestCaseZipProcessor:
    """
    Xử lý ZIP file chứa test cases
    Hỗ trợ nhiều format:
    1. Flat structure: test01.in, test01.out, test02.in, test02.out
    2. Folder structure: sample/01.in, sample/01.ans, secret/01.in, secret/01.ans
    3. Mixed extensions: .in/.out, .in/.ans
    """
    
    def __init__(self, zip_file, problem):
        self.zip_file = zip_file
        self.problem = problem
        self.test_cases_data = {}
        
    def process(self, auto_detect_type=True, default_type='secret', default_points=10.0):
        """
        Xử lý ZIP và tạo test cases
        Returns: {
            'created': int,
            'skipped': int,
            'errors': list[str]
        }
        """
        try:
            # 1. Extract và parse files từ ZIP
            self._extract_zip()
            
            # 2. Match input/output files
            matched_pairs = self._match_test_pairs()
            
            # 3. Create test cases
            result = self._create_test_cases(
                matched_pairs,
                auto_detect_type=auto_detect_type,
                default_type=default_type,
                default_points=default_points
            )
            
            return result
        
        except zipfile.BadZipFile:
            return {
                'created': 0,
                'skipped': 0,
                'errors': ['File ZIP không hợp lệ hoặc bị hỏng']
            }
        except Exception as e:
            return {
                'created': 0,
                'skipped': 0,
                'errors': [f'Lỗi xử lý ZIP: {str(e)}']
            }
    
    def _extract_zip(self):
        """Extract ZIP và lưu tạm vào memory"""
        with zipfile.ZipFile(self.zip_file, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                # Skip folders
                if file_info.is_dir():
                    continue
                
                # Skip hidden files và __MACOSX
                filename = file_info.filename
                if filename.startswith('.') or '__MACOSX' in filename:
                    continue
                
                # Read file content
                content = zip_ref.read(file_info)
                
                # Normalize path (replace \ with /)
                normalized_path = filename.replace('\\', '/')
                
                self.test_cases_data[normalized_path] = {
                    'content': content,
                    'size': file_info.file_size
                }
    
    def _match_test_pairs(self):
        """
        Match input/output files thành pairs
        Returns: [
            {
                'base_name': 'test01' hoặc 'sample/01',
                'folder': 'sample' | 'secret' | None,
                'sequence': 1,
                'input_path': 'test01.in',
                'output_path': 'test01.out',
                'input_content': b'...',
                'output_content': b'...'
            },
            ...
        ]
        """
        pairs = {}
        
        for path, data in self.test_cases_data.items():
            # Parse path: folder/filename.ext hoặc filename.ext
            parts = path.split('/')
            if len(parts) > 1:
                folder = parts[0]
                filename = parts[-1]
            else:
                folder = None
                filename = path
            
            # Parse filename: name.ext
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) != 2:
                continue
            
            base_name, ext = name_parts
            ext = ext.lower()
            
            # Chỉ xử lý .in, .out, .ans
            if ext not in ['in', 'out', 'ans']:
                continue
            
            # Create unique key cho pair
            if folder:
                pair_key = f"{folder}/{base_name}"
            else:
                pair_key = base_name
            
            # Initialize pair nếu chưa tồn tại
            if pair_key not in pairs:
                pairs[pair_key] = {
                    'base_name': base_name,
                    'folder': folder,
                    'sequence': self._extract_sequence(base_name),
                    'input_path': None,
                    'output_path': None,
                    'input_content': None,
                    'output_content': None
                }
            
            # Assign input hoặc output
            if ext == 'in':
                pairs[pair_key]['input_path'] = path
                pairs[pair_key]['input_content'] = data['content']
            elif ext in ['out', 'ans']:
                pairs[pair_key]['output_path'] = path
                pairs[pair_key]['output_content'] = data['content']
        
        # Chỉ giữ lại pairs có cả input VÀ output
        valid_pairs = [
            pair for pair in pairs.values()
            if pair['input_content'] is not None and pair['output_content'] is not None
        ]
        
        # Sort theo sequence
        valid_pairs.sort(key=lambda x: (x['folder'] or '', x['sequence']))
        
        return valid_pairs
    
    def _extract_sequence(self, base_name):
        """
        Extract sequence number từ base_name
        Ví dụ: '01' -> 1, 'test02' -> 2, 'sample_03' -> 3
        """
        # Tìm số cuối cùng trong tên
        match = re.search(r'(\d+)(?!.*\d)', base_name)
        if match:
            return int(match.group(1))
        return 0
    
    def _create_test_cases(self, matched_pairs, auto_detect_type, default_type, default_points):
        """Tạo TestCase objects từ matched pairs"""
        created = 0
        skipped = 0
        errors = []
        
        for idx, pair in enumerate(matched_pairs, start=1):
            try:
                # Determine type
                if auto_detect_type and pair['folder']:
                    folder_lower = pair['folder'].lower()
                    if 'sample' in folder_lower:
                        test_type = 'sample'
                    elif 'secret' in folder_lower or 'hidden' in folder_lower:
                        test_type = 'secret'
                    else:
                        test_type = default_type
                else:
                    test_type = default_type
                
                # Decode content to text
                try:
                    input_text = pair['input_content'].decode('utf-8')
                    output_text = pair['output_content'].decode('utf-8')
                except UnicodeDecodeError:
                    # Thử với latin-1 nếu utf-8 fail
                    try:
                        input_text = pair['input_content'].decode('latin-1')
                        output_text = pair['output_content'].decode('latin-1')
                    except:
                        errors.append(f"Không thể decode {pair['base_name']}: encoding không hợp lệ")
                        skipped += 1
                        continue
                
                # Determine sequence (ưu tiên sequence từ filename, nếu không thì dùng index)
                sequence = pair['sequence'] if pair['sequence'] > 0 else idx
                
                # Kiểm tra duplicate sequence
                if TestCase.objects.filter(problem=self.problem, sequence=sequence).exists():
                    # Auto increment sequence
                    max_seq = TestCase.objects.filter(problem=self.problem).aggregate(
                        max_seq=models.Max('sequence')
                    )['max_seq'] or 0
                    sequence = max_seq + 1
                
                # Create test case
                test_case = TestCase.objects.create(
                    problem=self.problem,
                    type=test_type,
                    sequence=sequence,
                    input_data=input_text,
                    output_data=output_text,
                    points=default_points
                )
                
                # Create File objects cho input/output (để sync với DOMjudge)
                input_file = self._create_file_object(
                    content=pair['input_content'],
                    filename=f"{self.problem.slug}_test{sequence}.in"
                )
                output_file = self._create_file_object(
                    content=pair['output_content'],
                    filename=f"{self.problem.slug}_test{sequence}.out"
                )
                
                test_case.input_file = input_file
                test_case.output_file = output_file
                test_case.save()
                
                created += 1
            
            except Exception as e:
                errors.append(f"Error creating test case from {pair['base_name']}: {str(e)}")
                skipped += 1
                continue
        
        return {
            'created': created,
            'skipped': skipped,
            'errors': errors
        }
    
    def _create_file_object(self, content, filename):
        """Tạo File object từ binary content"""
        file_obj = File()
        file_obj.filename = filename
        file_obj.storage_key.save(
            filename,
            ContentFile(content),
            save=False
        )
        file_obj.file_type = 'text/plain'
        file_obj.size = len(content)
        file_obj.save()
        return file_obj

