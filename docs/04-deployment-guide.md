# Deployment Guide: New Year Jeopardy Party Game

## Prerequisites

- AWS EC2 instance (Ubuntu 22.04 recommended)
- Domain name pointing to EC2 public IP
- GitHub repository with the code
- Telegram Bot token (from @BotFather)

---

## Part 1: EC2 Server Setup

### 1.1 Connect to EC2

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 1.2 Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Logout and login again for group changes
exit
```

### 1.3 Install Nginx & Certbot (for SSL)

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 1.4 Configure Firewall

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## Part 2: SSL Certificate

### 2.1 Configure Nginx for Domain

```bash
sudo nano /etc/nginx/sites-available/jeopardy
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For file uploads
        client_max_body_size 10M;
    }

    location /static/ {
        alias /home/ubuntu/jeopardy/app/static/;
    }

    location /uploads/ {
        alias /home/ubuntu/jeopardy/uploads/;
    }
}
```

### 2.2 Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/jeopardy /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 2.3 Get SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts. Certbot will automatically configure SSL.

---

## Part 3: Application Deployment

### 3.1 Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/your-username/jeopardy.git
cd jeopardy
```

### 3.2 Create Environment File

```bash
nano .env
```

```env
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
DATABASE_URL=sqlite:///instance/jeopardy.db
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=5242880
```

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.3 Create Docker Compose Production File

```bash
nano docker-compose.prod.yml
```

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./instance:/app/instance
      - ./uploads:/app/uploads
    env_file:
      - .env
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 3.4 Build and Run

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3.5 Initialize Database

```bash
docker compose -f docker-compose.prod.yml exec app flask db upgrade
```

### 3.6 Verify Deployment

```bash
# Check container is running
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Test endpoint
curl https://your-domain.com/
```

---

## Part 4: GitHub Actions CI/CD

### 4.1 Create Deploy Workflow

Create `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy to EC2

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ubuntu/jeopardy
            git pull origin main
            docker compose -f docker-compose.prod.yml up -d --build
            docker image prune -f
```

### 4.2 Configure GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Value |
|-------------|-------|
| `EC2_HOST` | Your EC2 public IP or domain |
| `EC2_SSH_KEY` | Contents of your EC2 private key (.pem file) |

### 4.3 Test CI/CD

1. Make a small change to your code
2. Push to `main` branch
3. Go to Actions tab to watch deployment
4. Verify changes on your server

---

## Part 5: Telegram Bot Configuration

### 5.1 Configure Mini App in BotFather

1. Open Telegram, go to @BotFather
2. Send `/mybots`
3. Select your bot (`svoya_jeopardy_bot`)
4. Select "Bot Settings"
5. Select "Menu Button"
6. Select "Configure menu button"
7. Enter your Mini App URL: `https://your-domain.com`
8. Enter button text: "🎮 Play Jeopardy"

### 5.2 Configure Web App URL

1. In BotFather, select your bot
2. Select "Bot Settings"
3. Select "Web App Info"
4. Enter your app URL: `https://your-domain.com`

### 5.3 Test Mini App

1. Open Telegram
2. Go to your bot
3. Click the menu button or send `/start`
4. Mini App should open

---

## Part 6: Maintenance

### 6.1 View Logs

```bash
# All logs
docker compose -f docker-compose.prod.yml logs -f

# Just app logs
docker compose -f docker-compose.prod.yml logs -f app
```

### 6.2 Backup Database

```bash
# Create backup
cp /home/ubuntu/jeopardy/instance/jeopardy.db /home/ubuntu/backups/jeopardy-$(date +%Y%m%d).db

# Setup daily backup cron
crontab -e
# Add: 0 2 * * * cp /home/ubuntu/jeopardy/instance/jeopardy.db /home/ubuntu/backups/jeopardy-$(date +\%Y\%m\%d).db
```

### 6.3 Restart Application

```bash
cd /home/ubuntu/jeopardy
docker compose -f docker-compose.prod.yml restart
```

### 6.4 Update Application Manually

```bash
cd /home/ubuntu/jeopardy
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

### 6.5 SSL Certificate Renewal

Certbot sets up automatic renewal. Verify with:

```bash
sudo certbot renew --dry-run
```

---

## Part 7: Troubleshooting

### App Not Loading

```bash
# Check if container is running
docker compose -f docker-compose.prod.yml ps

# Check container logs
docker compose -f docker-compose.prod.yml logs app

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Database Issues

```bash
# Access database
docker compose -f docker-compose.prod.yml exec app sqlite3 /app/instance/jeopardy.db

# Check tables
.tables

# Check data
SELECT * FROM games;
```

### Permission Issues

```bash
# Fix upload folder permissions
sudo chown -R 1000:1000 /home/ubuntu/jeopardy/uploads
sudo chmod -R 755 /home/ubuntu/jeopardy/uploads
```

### SSL Issues

```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start app | `docker compose -f docker-compose.prod.yml up -d` |
| Stop app | `docker compose -f docker-compose.prod.yml down` |
| View logs | `docker compose -f docker-compose.prod.yml logs -f` |
| Restart | `docker compose -f docker-compose.prod.yml restart` |
| Rebuild | `docker compose -f docker-compose.prod.yml up -d --build` |
| SSH to container | `docker compose -f docker-compose.prod.yml exec app /bin/sh` |
| Backup DB | `cp instance/jeopardy.db backups/jeopardy-backup.db` |

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_APP` | Flask application entry point | `app` |
| `FLASK_ENV` | Environment mode | `production` |
| `SECRET_KEY` | Flask secret key (generate random) | `abc123...` |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | `123456:ABC-DEF...` |
| `DATABASE_URL` | SQLite database path | `sqlite:///instance/jeopardy.db` |
| `UPLOAD_FOLDER` | Path for uploaded images | `/app/uploads` |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | `5242880` (5MB) |
