# Xây dựng Website học và thi lập trình trực tuyến (Django + ReactJS + MySQL)

## Giới thiệu
Dự án **Hệ thống học và thi lập trình trực tuyến** nhằm cung cấp một nền tảng toàn diện cho việc **học lập trình**, **luyện tập**, và **thi đấu**.  
Hệ thống tích hợp **học lý thuyết, thực hành, thi lập trình**, **leaderboard realtime**, và **AI chatbot hỗ trợ học tập**.

- **Backend**: Django (Python) – REST API, xử lý logic, chấm bài tự động.  
- **Frontend**: ReactJS – giao diện hiện đại, phản hồi nhanh.  
- **Database**: MySQL – lưu trữ người dùng, khóa học, bài nộp, cuộc thi.  

---

## Mục tiêu hệ thống
1. **Tạo môi trường học tập linh hoạt** – học mọi lúc, mọi nơi, với nhiều ngôn ngữ lập trình.  
2. **Thúc đẩy thực hành & đánh giá tự động** – chấm điểm code trực tuyến, cung cấp feedback tức thì.  
3. **Xây dựng cộng đồng lập trình** – diễn đàn hỏi đáp, chatbot AI hỗ trợ học tập.  

---

## Chức năng chi tiết

### Dành cho người dùng (Student)
- Đăng ký/Đăng nhập, quản lý hồ sơ học tập.  
- Quản lý khóa học: tìm kiếm, lọc theo ngôn ngữ, trình độ.  
- Học trực tuyến: video, tài liệu PDF/slide.  
- **Code editor online**: chạy code nhiều ngôn ngữ.  
- Nộp bài lập trình, chấm điểm tự động (Accepted, Wrong Answer, TLE, MLE, RTE).  
- Leaderboard realtime & bảng xếp hạng tổng.  
- Làm quiz, bài tập trắc nghiệm, thi đấu contest.  
- Diễn đàn thảo luận, bình luận dưới mỗi bài học/bài tập.  

### Dành cho quản trị viên (Admin)
- Quản lý khóa học, bài học, quiz.  
- Quản lý bài toán lập trình & testcase.  
- Tổ chức contest (thời gian, bài tập, chế độ private/public).  
- Quản lý người dùng & phân quyền.  
- Thống kê, báo cáo học viên, khóa học, doanh thu.  
- Quản lý diễn đàn.  

### Tích hợp AI
- Chatbot hỗ trợ học tập: giải đáp thắc mắc, gợi ý tài liệu, hỗ trợ lập trình.  

---

## Cấu trúc cơ sở dữ liệu (MySQL)

Một số bảng chính:
- `users` – người dùng (student/admin)  
- `courses`, `lessons`, `enrollments` – khóa học & tham gia  
- `quizzes`, `quiz_questions`, `quiz_submissions` – bài thi trắc nghiệm  
- `problems`, `problem_tests`, `submissions` – bài toán & bài nộp  
- `contests`, `contest_problems`, `contest_participants`, `contest_submissions`, `contest_leaderboard` – thi đấu lập trình  
- `leaderboards` – bảng xếp hạng tổng  
- `forums`, `forum_posts`, `forum_comments` – diễn đàn  
- `payments`, `orders`, `order_items` – giao dịch khóa học  

---

## Kiến trúc hệ thống
- **Backend (Django)**: REST API, xử lý logic nghiệp vụ, kết nối MySQL.  
- **Frontend (ReactJS)**: SPA (Single Page Application), giao diện động, gọi API từ backend.  
- **Database (MySQL)**: lưu trữ dữ liệu, hỗ trợ truy vấn nhanh.  

---