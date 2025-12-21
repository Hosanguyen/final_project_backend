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

## Hướng dẫn triển khai nhanh (Docker)

### Bước 1: Build DOMjudge để lấy admin password
```powershell
cd backend
docker-compose -f docker-compose.production.yml up -d db domserver
```

Đợi 30-60 giây để DOMjudge khởi tạo, sau đó lấy admin password:
```powershell
docker logs domjudge_server 2>&1 | Select-String "Initial admin password"
```

### Bước 2: Cập nhật password vào file .env
Mở file `.env` và cập nhật:
```env
DOMJUDGE_USERNAME=admin
DOMJUDGE_PASSWORD=<password_vừa_lấy_được>
```

### Bước 3: Build toàn bộ hệ thống
```powershell
docker-compose -f docker-compose.production.yml up -d
```

### Bước 4: Khởi tạo dữ liệu
```powershell
# Tạo admin user và practice contest
docker exec django_backend python manage.py init_permissions
```

### Truy cập hệ thống
- **Django Admin**: http://localhost/admin/ (username: `admin`, password: `admin123`)
- **DOMjudge**: http://localhost/domjudge/ (username: `admin`, password: `<từ bước 1>`)
- **API Docs**: http://localhost/api/

### Lệnh hữu ích
```powershell
# Xem logs Django
docker logs -f django_backend

# Xem logs DOMjudge
docker logs -f domjudge_server

# Restart toàn bộ hệ thống
docker-compose -f docker-compose.production.yml restart

# Dừng hệ thống
docker-compose -f docker-compose.production.yml down

# Xem thêm: DOCKER_COMMANDS.md
```

---

## 3.1.2.4. Triển khai

### a. Kiến trúc triển khai

Hệ thống được triển khai theo mô hình **containerization** sử dụng **Docker Compose**, bao gồm 6 services chính:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx Reverse Proxy                      │
│                          (Port 80/443)                          │
└───────────┬─────────────────────────────────────┬───────────────┘
            │                                     │
            ▼                                     ▼
    ┌───────────────┐                   ┌──────────────────┐
    │ Django Backend│                   │  DOMjudge Server │
    │   (Gunicorn)  │◄─────────────────►│   (Apache+PHP)   │
    │   Port 8000   │   API Calls       │    Port 8088     │
    └───────┬───────┘                   └─────────┬────────┘
            │                                     │
            │                                     │
            ▼                                     ▼
    ┌───────────────┐                   ┌──────────────────┐
    │  MySQL 8.0    │                   │  MariaDB 10.6    │
    │  (Django DB)  │                   │  (DOMjudge DB)   │
    │   Port 3307   │                   │   Port 13306     │
    └───────────────┘                   └─────────┬────────┘
                                                  │
                                                  ▼
                                        ┌──────────────────┐
                                        │  Judgehost       │
                                        │  (Code Executor) │
                                        └──────────────────┘
```

### b. Các thành phần triển khai

#### 1. **Django Backend Container**
- **Base Image**: Python 3.11-slim
- **WSGI Server**: Gunicorn 21.2.0 (4 workers, 2 threads/worker)
- **Dependencies**: 
  - Django 4.2.7, DRF 3.14.0
  - Data science stack: pandas, numpy, scipy, scikit-learn
  - MySQL client libraries, python-dateutil, requests
- **Chức năng**: 
  - REST API endpoints
  - Tích hợp DOMjudge qua API
  - Tích hợp VNPay payment
  - Rating calculation, leaderboard
- **Health Check**: Kiểm tra database connection trước khi khởi động

#### 2. **MySQL 8.0 (Django Database)**
- **Port**: 3307 (host) → 3306 (container)
- **Database**: `dbtest_finalproject`
- **Volume**: Persistent storage cho user data, courses, submissions
- **Charset**: utf8mb4 (hỗ trợ Unicode đầy đủ)

#### 3. **DOMjudge Server**
- **Version**: 9.0.0
- **Components**: Apache, PHP 8.x, DOMjudge webapp
- **Port**: 8088 (direct access), 80 (via Nginx /domjudge/)
- **Chức năng**: 
  - Quản lý contests, problems, submissions
  - API cho Django backend
  - Web UI cho admin

#### 4. **MariaDB 10.6 (DOMjudge Database)**
- **Port**: 13306 (host) → 3306 (container)
- **Database**: `domjudge`
- **Read-only Access**: Django backend chỉ đọc dữ liệu submissions

#### 5. **Judgehost**
- **Chức năng**: Chấm bài tự động trong sandbox môi trường
- **Privileged Mode**: Cần quyền để tạo isolated execution environment
- **Supported Languages**: C, C++, Java, Python, JavaScript, Go, Rust

#### 6. **Nginx Reverse Proxy**
- **Port**: 80 (HTTP), 443 (HTTPS - optional)
- **Routing**:
  - `/api/` → Django Backend (rate limit: 10 req/s)
  - `/admin/` → Django Admin
  - `/domjudge/` → DOMjudge Server
  - `/static/` → Django static files (cache 30 days)
  - `/media/` → User uploads (cache 7 days)
  - `/` → Redirect to `/domjudge/`
- **Features**: 
  - Rate limiting
  - Gzip compression
  - Security headers (X-Frame-Options, X-Content-Type-Options)
  - Static file caching

### c. Quy trình triển khai

#### **Bước 1: Chuẩn bị môi trường**
```powershell
# Clone repository
git clone <repository_url>
cd backend

# Tạo file .env từ example
copy example.env .env
```

#### **Bước 2: Build DOMjudge và lấy admin password**
```powershell
# Khởi động DOMjudge server trước
docker-compose -f docker-compose.production.yml up -d db domserver

# Đợi 30-60 giây để khởi tạo, sau đó lấy password
docker logs domjudge_server 2>&1 | Select-String "Initial admin password"
```

#### **Bước 3: Cấu hình biến môi trường**
Cập nhật file `.env` với thông tin vừa lấy được:
```env
# Django Database
MAIN_DB_NAME=dbtest_finalproject
MYSQL_ROOT_PASSWORD=rootpw
DJANGO_DB_HOST=django_db
DJANGO_DB_PORT=3306

# DOMjudge Database (read-only)
DOMJUDGE_DB_HOST=db
DOMJUDGE_DB_PORT=3306
DOMJUDGE_DB_NAME=domjudge
DOMJUDGE_DB_USER=domjudge
DOMJUDGE_DB_PASSWORD=djpw

# DOMjudge API
DOMJUDGE_API_URL=http://domserver:80/api/v4
DOMJUDGE_USERNAME=admin
DOMJUDGE_PASSWORD=<password_từ_bước_2>

# Django Admin
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin123
DJANGO_SUPERUSER_EMAIL=admin@example.com

# VNPay (optional - production only)
VNPAY_TMN_CODE=your_tmn_code
VNPAY_HASH_SECRET=your_hash_secret
VNPAY_PAYMENT_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://localhost/api/vnpay/return/
```

#### **Bước 4: Build toàn bộ hệ thống**
```powershell
# Build và khởi động tất cả services
docker-compose -f docker-compose.production.yml up -d

# Kiểm tra status
docker-compose -f docker-compose.production.yml ps
```

#### **Bước 5: Khởi tạo dữ liệu**
```powershell
# Chạy migrations
docker exec django_backend python manage.py migrate

# Tạo admin user, roles, permissions, practice contest
docker exec django_backend python manage.py init_permissions

# Collect static files
docker exec django_backend python manage.py collectstatic --noinput
```

#### **Bước 6: Xác minh triển khai**
- **Django Admin**: http://localhost/admin/ (admin/admin123)
- **DOMjudge**: http://localhost/domjudge/ (admin/<password_bước_2>)
- **API Documentation**: http://localhost/api/
- **Health Check**: http://localhost/health/

### d. Cấu hình Production

#### **Docker Compose Configuration**
```yaml
version: '3.8'

services:
  django_backend:
    build: .
    container_name: django_backend
    command: >
      sh -c "gunicorn backend.wsgi:application 
             --bind 0.0.0.0:8000 
             --workers 4 
             --threads 2 
             --timeout 120 
             --access-logfile - 
             --error-logfile -"
    environment:
      - DJANGO_SETTINGS_MODULE=backend.settings
    depends_on:
      - django_db
      - db
      - domserver
    networks:
      - app_network
      - dj_net
```

#### **Nginx Configuration Highlights**
```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Django API
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://django_backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# Static files with caching
location /static/ {
    alias /app/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### e. Monitoring và Maintenance

#### **Xem Logs**
```powershell
# Logs tất cả services
docker-compose -f docker-compose.production.yml logs -f

# Logs Django backend
docker logs -f django_backend

# Logs DOMjudge
docker logs -f domjudge_server

# Filter errors
docker logs django_backend 2>&1 | Select-String "Error|Exception"
```

#### **Database Backup**
```powershell
# Backup Django database
docker exec django_mysql mysqldump -uroot -prootpw dbtest_finalproject | gzip > "backup_$(Get-Date -Format 'yyyyMMdd').sql.gz"

# Backup DOMjudge database
docker exec domjudge_mariadb mysqldump -udomjudge -pdjpw domjudge | gzip > "domjudge_backup_$(Get-Date -Format 'yyyyMMdd').sql.gz"

# Backup media files
Compress-Archive -Path ./media -DestinationPath "media_backup_$(Get-Date -Format 'yyyyMMdd').zip"
```

#### **Resource Monitoring**
```powershell
# CPU, Memory usage
docker stats

# Disk usage
docker system df

# Container health
docker inspect django_backend | Select-String "Health"
```

#### **Scaling**
```powershell
# Tăng số lượng Gunicorn workers (sửa trong docker-compose.yml)
command: gunicorn backend.wsgi:application --workers 8

# Thêm judgehost để tăng throughput chấm bài
docker-compose -f docker-compose.production.yml up -d --scale judgehost=3
```

### f. Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| Container không start | Port conflict | `netstat -ano \| findstr :8000` → Đổi port |
| Database connection failed | Wrong credentials | Kiểm tra `.env` và `docker-compose.yml` |
| DOMjudge 401 Unauthorized | Wrong API password | Lấy lại password từ logs: `docker logs domjudge_server` |
| Submission không được chấm | Judgehost down | `docker-compose restart judgehost` |
| Out of disk space | Log files, volumes | `docker system prune -a --volumes` |
| High memory usage | Too many workers | Giảm số workers trong Gunicorn config |

### g. Security Considerations

1. **HTTPS**: Uncomment port 443 trong docker-compose.yml, thêm SSL certificates vào `nginx/ssl/`
2. **Firewall**: Chỉ expose port 80/443, block direct access 8000/8088
3. **Database**: Thay đổi default passwords trong production
4. **API Rate Limiting**: Đã configure trong Nginx (10 req/s)
5. **CORS**: Configure trong Django settings cho frontend domain
6. **Environment Variables**: Không commit `.env` file lên Git

### h. Performance Optimization

1. **Database Indexing**: Đã index các trường thường xuyên query (user_id, contest_id, problem_id)
2. **Caching**: Django cache framework cho leaderboard, course list
3. **Static Files**: CDN cho production (CloudFront, Cloudflare)
4. **Database Connection Pooling**: Sử dụng persistent connections
5. **Nginx Caching**: Static files cache 30 days, API responses no-cache
6. **Gunicorn Tuning**: Workers = (2 × CPU cores) + 1

Tham khảo thêm: [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) để biết các lệnh Docker thường dùng.

---