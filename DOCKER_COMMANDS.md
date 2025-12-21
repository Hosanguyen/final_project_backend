# Docker Commands Cheat Sheet

## 🚀 Container Management

### Khởi động/Dừng Services
```powershell
# Khởi động tất cả services
docker-compose -f docker-compose.production.yml up -d

# Khởi động service cụ thể
docker-compose -f docker-compose.production.yml up -d django_backend

# Dừng tất cả services
docker-compose -f docker-compose.production.yml down

# Dừng service cụ thể
docker-compose -f docker-compose.production.yml stop django_backend

# Restart service
docker-compose -f docker-compose.production.yml restart django_backend

# Rebuild và restart
docker-compose -f docker-compose.production.yml up -d --build django_backend

# Force recreate container (xóa và tạo mới)
docker-compose -f docker-compose.production.yml up -d --force-recreate django_backend
```

### Kiểm tra Status
```powershell
# Xem tất cả containers đang chạy
docker-compose -f docker-compose.production.yml ps

# Xem tất cả containers (kể cả stopped)
docker ps -a

# Xem resource usage (CPU, Memory)
docker stats

# Xem thông tin chi tiết container
docker inspect django_backend
```

## 📋 Logs & Debugging

### Xem Logs
```powershell
# Xem logs real-time (follow)
docker logs -f django_backend

# Xem 50 dòng logs cuối
docker logs --tail 50 django_backend

# Xem logs với timestamp
docker logs -t django_backend

# Xem logs từ 10 phút trước
docker logs --since 10m django_backend

# Xem logs của tất cả services
docker-compose -f docker-compose.production.yml logs -f
```

### Container Shell Access
```powershell
# Vào shell của Django container
docker exec -it django_backend bash

# Vào shell của MySQL container
docker exec -it django_mysql bash

# Vào shell của DOMjudge MariaDB
docker exec -it domjudge_mariadb bash

# Vào shell của Nginx
docker exec -it nginx_proxy sh
```

## 🐍 Django Management Commands

### Chạy Django Commands
```powershell
# Django shell
docker exec -it django_backend python manage.py shell

# Run migrations
docker exec django_backend python manage.py migrate

# Create migrations
docker exec django_backend python manage.py makemigrations

# Collect static files
docker exec django_backend python manage.py collectstatic --noinput

# Create superuser (interactive)
docker exec -it django_backend python manage.py createsuperuser

# Initialize permissions
docker exec django_backend python manage.py init_permissions

# Run custom command
docker exec django_backend python manage.py shell -c "from users.models import User; print(User.objects.count())"
```

## 🗄️ Database Operations

### Django MySQL
```powershell
# Connect to MySQL
docker exec -it django_mysql mysql -uroot -prootpw dbtest_finalproject

# Run query
docker exec django_mysql mysql -uroot -prootpw dbtest_finalproject -e "SELECT * FROM users LIMIT 5"

# Backup database
docker exec django_mysql mysqldump -uroot -prootpw dbtest_finalproject > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Restore database
Get-Content backup.sql | docker exec -i django_mysql mysql -uroot -prootpw dbtest_finalproject

# Show databases
docker exec django_mysql mysql -uroot -prootpw -e "SHOW DATABASES"

# Show tables
docker exec django_mysql mysql -uroot -prootpw dbtest_finalproject -e "SHOW TABLES"
```

### DOMjudge MariaDB
```powershell
# Connect to MariaDB
docker exec -it domjudge_mariadb mysql -udomjudge -pdjpw domjudge

# Run query
docker exec domjudge_mariadb mysql -udomjudge -pdjpw domjudge -e "SELECT * FROM contest"

# Show tables
docker exec domjudge_mariadb mysql -udomjudge -pdjpw domjudge -e "SHOW TABLES"
```

### DOMjudge Admin Credentials
```powershell
# Lấy admin password (từ logs khi container khởi động lần đầu)
docker logs domjudge_server 2>&1 | Select-String -Pattern "admin.*password" | Select-Object -First 5

# Lấy judgehost password
docker logs domjudge_server 2>&1 | Select-String -Pattern "judgehost.*password" | Select-Object -First 5

# Access DOMjudge web interface
# URL: http://localhost:8088/ hoặc http://localhost/domjudge/
# Username: admin
# Password: (lấy từ command trên)
```

## 📁 File Operations

### Copy Files To/From Containers
```powershell
# Copy file từ host vào container
docker cp local_file.txt django_backend:/app/

# Copy file từ container ra host
docker cp django_backend:/app/file.txt ./

# Copy folder
docker cp ./media django_backend:/app/media

# View file content
docker exec django_backend cat /app/requirements.txt

# Edit file (vi)
docker exec -it django_backend vi /app/settings.py

# List files
docker exec django_backend ls -la /app/
```

## 🔍 Network & Ports

### Network Inspection
```powershell
# List networks
docker network ls

# Inspect network
docker network inspect app_network

# Check open ports
docker port django_backend

# Test connection giữa containers
docker exec django_backend ping domserver
docker exec django_backend nc -zv django_db 3306
```

## 🧹 Cleanup

### Clean Up Resources
```powershell
# Xóa tất cả stopped containers
docker container prune

# Xóa tất cả unused images
docker image prune -a

# Xóa tất cả unused volumes
docker volume prune

# Xóa tất cả unused networks
docker network prune

# Xóa tất cả (CẨNTHẬN!)
docker system prune -a --volumes

# Xóa volume cụ thể
docker volume rm django_mysql_data
```

### Remove Specific Containers
```powershell
# Stop và remove container
docker-compose -f docker-compose.production.yml down django_backend

# Remove container (force)
docker rm -f django_backend

# Remove image
docker rmi backend-django_backend
```

## 📊 Monitoring

### Resource Usage
```powershell
# Xem resource usage real-time
docker stats

# Xem resource của container cụ thể
docker stats django_backend

# Xem disk usage
docker system df

# Xem chi tiết disk usage
docker system df -v
```

## 🔐 Security & Permissions

### File Permissions
```powershell
# Change file permissions trong container
docker exec django_backend chmod +x /app/script.sh

# Change owner
docker exec django_backend chown -R www-data:www-data /app/media

# Check permissions
docker exec django_backend ls -la /app/
```

## 🔄 Quick Tasks

### Common Operations
```powershell
# Restart toàn bộ hệ thống
docker-compose -f docker-compose.production.yml restart

# Rebuild Django sau khi sửa code
docker-compose -f docker-compose.production.yml up -d --build django_backend

# Xem logs lỗi Django
docker logs django_backend 2>&1 | Select-String -Pattern "Error|Exception|Traceback"

# Kiểm tra health của containers
docker inspect django_backend | Select-String -Pattern "Health"

# Execute SQL query nhanh
docker exec django_mysql mysql -uroot -prootpw -e "USE dbtest_finalproject; SELECT COUNT(*) FROM users;"

# Clear Django cache (nếu có redis)
docker exec django_backend python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Lấy DOMjudge admin password
docker logs domjudge_server 2>&1 | Select-String "Initial admin password"

# Lấy Django admin credentials (từ .env)
Get-Content .env | Select-String "DJANGO_SUPERUSER"
```

## 🎯 Production Operations

### Deploy Updates
```powershell
# 1. Pull latest code
git pull origin main

# 2. Rebuild containers
docker-compose -f docker-compose.production.yml build

# 3. Stop old containers
docker-compose -f docker-compose.production.yml down

# 4. Start new containers
docker-compose -f docker-compose.production.yml up -d

# 5. Run migrations
docker exec django_backend python manage.py migrate

# 6. Collect static files
docker exec django_backend python manage.py collectstatic --noinput

# 7. Check logs
docker logs -f django_backend
```

### Backup Strategy
```powershell
# Backup Django database
docker exec django_mysql mysqldump -uroot -prootpw dbtest_finalproject | gzip > "django_db_$(Get-Date -Format 'yyyyMMdd').sql.gz"

# Backup DOMjudge database
docker exec domjudge_mariadb mysqldump -udomjudge -pdjpw domjudge | gzip > "domjudge_db_$(Get-Date -Format 'yyyyMMdd').sql.gz"

# Backup media files
Compress-Archive -Path ./media -DestinationPath "media_backup_$(Get-Date -Format 'yyyyMMdd').zip"

# Backup docker volumes
docker run --rm -v django_mysql_data:/data -v ${PWD}:/backup alpine tar czf /backup/django_mysql_data_backup.tar.gz -C /data .
```

## 🚨 Troubleshooting

### Common Issues
```powershell
# Container không start
docker logs django_backend
docker inspect django_backend

# Port conflict
netstat -ano | findstr :8000
docker ps -a

# Network issues
docker network inspect app_network
docker exec django_backend ping django_db

# Database connection failed
docker exec django_backend nc -zv django_db 3306
docker exec django_mysql mysql -uroot -prootpw -e "SELECT 1"

# Permission denied
docker exec django_backend ls -la /app/
docker exec django_backend chmod -R 755 /app/

# Out of disk space
docker system df
docker system prune -a
```

## 💡 Tips

### Useful Aliases (PowerShell Profile)
```powershell
# Thêm vào $PROFILE để dùng nhanh

function dps { docker ps }
function dpsa { docker ps -a }
function dlog { docker logs -f $args }
function dexec { docker exec -it $args }
function dshell { docker exec -it $args bash }
function dcom { docker-compose -f docker-compose.production.yml $args }
```

### Environment Variables
```powershell
# Load .env file
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
```

---

## 📚 References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Docker Guide](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [DOMjudge Documentation](https://www.domjudge.org/docs/)
