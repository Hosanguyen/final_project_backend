Tạo component js submissions có thể edit trong code editor trong trang chi tiết problems với các ngôn ngữ có thể chọn được cấu hình trong mỗi problem và sau đó submit về backend python và từ backend submit lên domjude qua API để chấm bài thi
VD API domjudge
http://localhost:8088/api/v4/contests/{cid}/submissions
requests body multipart/form-data
problem
string
The problem to submit a solution for

problem_id
string
The problem to submit a solution for

language
string
The language to submit a solution in

language_id
string
The language to submit a solution in

team_id
string
The team to submit a solution for. Only used when adding a submission as admin

user_id
string
The user to submit a solution for. Only used when adding a submission as admin

time
string($date-time)
The time to use for the submission. Only used when adding a submission as admin

entry_point
string
The entry point for the submission. Required for languages requiring an entry point

id
string
The ID to use for the submission. Only used when adding a submission as admin and only allowed with PUT

files
array<object>
The base64 encoded ZIP file to submit

code
file
The file(s) to submit

response:
{
  "language_id": "string",
  "time": "string",
  "contest_time": "string",
  "team_id": "string",
  "problem_id": "string",
  "files": [
    {
      "href": "string",
      "mime": "string",
      "filename": "string"
    }
  ],
  "submitid": 0,
  "id": "string",
  "entry_point": "string",
  "import_error": "string"
}