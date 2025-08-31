# Docker Commands Reference

## 🐳 Food App Container Management

### **Container Lifecycle**

#### **Start the App**

```bash
# Start the app with the automated script
./run_local.sh

# Or manually start the container
docker run -d -p 8000:8000 --env-file test-local.env -v $(pwd)/instance:/app/instance --name food-app-container food-app
```

#### **Stop the Container**

```bash
# Stop the container
docker stop food-app-container

# Stop and remove the container
docker stop food-app-container && docker rm food-app-container
```

#### **Restart the Container**

```bash
# Restart the container
docker restart food-app-container

# Stop, remove, and recreate the container
docker stop food-app-container && docker rm food-app-container && ./run_local.sh
```

### **Logs & Monitoring**

#### **Live Logs (Real-time)**

```bash
# Follow logs in real-time (like tail -f)
docker logs food-app-container --follow

# Shorter version
docker logs food-app-container -f
```

#### **Recent Logs**

```bash
# Show last 20 lines
docker logs food-app-container --tail 20

# Show last 50 lines
docker logs food-app-container --tail 50

# Show all logs
docker logs food-app-container
```

#### **Timestamped Logs**

```bash
# Show logs with timestamps
docker logs food-app-container --timestamps

# Follow with timestamps
docker logs food-app-container -f --timestamps
```

#### **Time-based Logs**

```bash
# Show logs since last 10 minutes
docker logs food-app-container --since 10m

# Show logs since last hour
docker logs food-app-container --since 1h

# Show logs since specific time
docker logs food-app-container --since "2025-07-18T14:00:00"
```

#### **Combined Options**

```bash
# Follow with timestamps and show last 10 lines
docker logs food-app-container -f --timestamps --tail 10

# Show recent logs with timestamps
docker logs food-app-container --timestamps --tail 20
```

### **Container Status & Information**

#### **Check Container Status**

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Check if specific container is running
docker ps | grep food-app-container
```

#### **Container Information**

```bash
# Get detailed container info
docker inspect food-app-container

# Get container resource usage
docker stats food-app-container

# Get container logs size
docker logs food-app-container --tail 0
```

### **Database & File Management**

#### **Database Operations**

```bash
# Access the container shell
docker exec -it food-app-container /bin/bash

# Check database file permissions
docker exec food-app-container ls -la /app/instance/

# Test database connection
docker exec food-app-container python3 -c "import sqlite3; conn = sqlite3.connect('/app/instance/local.db'); print('Database connection successful'); conn.close()"

# Initialize database tables
docker exec food-app-container python3 -c "from src.app import app, db; app.app_context().push(); db.create_all(); print('Database tables created successfully')"
```

#### **File Operations**

```bash
# Copy files from container to host
docker cp food-app-container:/app/instance/local.db ./backup_local.db

# Copy files from host to container
docker cp ./some_file.txt food-app-container:/app/

# View files in container
docker exec food-app-container ls -la /app/
docker exec food-app-container ls -la /app/src/
```

### **Environment & Configuration**

#### **Environment Variables**

```bash
# Check environment variables in container
docker exec food-app-container env | grep -E "(DATABASE|AZURE|CLAUDE)"

# Set environment variable in running container
docker exec food-app-container bash -c "export NEW_VAR=value"
```

#### **Configuration Files**

```bash
# View config files in container
docker exec food-app-container cat /app/src/config.json
docker exec food-app-container cat /app/test-local.env

# Edit config files (if needed)
docker exec -it food-app-container /bin/bash
# Then edit files with nano or vim
```

### **Debugging & Troubleshooting**

#### **Container Debugging**

```bash
# Access container shell for debugging
docker exec -it food-app-container /bin/bash

# Check container logs for errors
docker logs food-app-container | grep -i error

# Check container logs for warnings
docker logs food-app-container | grep -i warning
```

#### **Network & Connectivity**

```bash
# Check container network
docker network ls
docker network inspect bridge

# Test container connectivity
docker exec food-app-container ping google.com

# Check port mappings
docker port food-app-container
```

#### **Resource Usage**

```bash
# Monitor container resources
docker stats food-app-container

# Check container disk usage
docker exec food-app-container df -h

# Check container memory usage
docker exec food-app-container free -h
```

### **Cleanup & Maintenance**

#### **Cleanup Commands**

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup (use with caution)
docker system prune -a
```

#### **Container Maintenance**

```bash
# Update container (rebuild image)
docker build -t food-app .

# Remove old container and create new one
docker stop food-app-container && docker rm food-app-container && ./run_local.sh
```

### **Development Workflow**

#### **Quick Development Commands**

```bash
# Start development environment
./run_local.sh

# View live logs while testing
docker logs food-app-container -f

# Restart container after code changes
docker restart food-app-container

# Check app health
curl -I http://localhost:8000
```

#### **Testing Commands**

```bash
# Test database connection
docker exec food-app-container python3 -c "from src.app import app, db; print('Database connection OK')"

# Test Azure services (if enabled)
docker exec food-app-container python3 -c "from src.app import document_analysis_client; print('Azure services:', 'OK' if document_analysis_client else 'Disabled')"

# Test Claude API
docker exec food-app-container python3 -c "import os; print('Claude API Key:', 'Set' if os.getenv('CLAUDE_API_KEY') else 'Not Set')"
```

### **Production Commands**

#### **Production Deployment**

```bash
# Build production image
docker build -t food-app:production .

# Run with production environment
docker run -d -p 8000:8000 --env-file .env --name food-app-prod food-app:production

# Check production logs
docker logs food-app-prod -f
```

### **Useful Aliases**

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Food app aliases
alias food-logs="docker logs food-app-container -f"
alias food-status="docker ps | grep food-app-container"
alias food-restart="docker restart food-app-container"
alias food-shell="docker exec -it food-app-container /bin/bash"
alias food-stop="docker stop food-app-container"
alias food-start="./run_local.sh"
```

### **Troubleshooting Common Issues**

#### **Container Won't Start**

```bash
# Check container logs for startup errors
docker logs food-app-container

# Check if port 8000 is already in use
lsof -i :8000

# Remove conflicting container
docker rm -f food-app-container
```

#### **Database Issues**

```bash
# Check database file permissions
docker exec food-app-container ls -la /app/instance/

# Fix database permissions
docker exec food-app-container chmod 666 /app/instance/local.db

# Recreate database
docker exec food-app-container rm /app/instance/local.db
docker exec food-app-container touch /app/instance/local.db
docker exec food-app-container chmod 666 /app/instance/local.db
```

#### **App Not Responding**

```bash
# Check if container is running
docker ps | grep food-app-container

# Check if app is listening on port 8000
docker exec food-app-container netstat -tlnp | grep 8000

# Restart the container
docker restart food-app-container
```

---

## 🎯 Quick Reference

**Most Used Commands:**

- `./run_local.sh` - Start the app
- `docker logs food-app-container -f` - Watch logs live
- `docker restart food-app-container` - Restart container
- `docker exec -it food-app-container /bin/bash` - Access shell
- `docker stop food-app-container` - Stop container

**For Development:**

- Use `docker logs -f` to watch logs while testing
- Use `docker restart` after code changes
- Use `docker exec` to run commands inside container

**For Production:**

- Use `docker stats` to monitor resources
- Use `docker logs --since` to check recent activity
- Use `docker exec` for maintenance tasks
