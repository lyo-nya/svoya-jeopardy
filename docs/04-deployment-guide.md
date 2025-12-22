# Deployment Guide: New Year Jeopardy Party Game

## Overview

We'll deploy to **Railway**, which provides:
- Free HTTPS subdomain (`*.railway.app`)
- Auto-deploy on push to GitHub
- Persistent storage for SQLite and uploaded images
- Zero server configuration

**Total deployment time: ~30 minutes**

---

## Prerequisites

- GitHub account with the code repository
- Railway account (free, sign up with GitHub)
- Telegram Bot token (from @BotFather)

---

## Part 1: Prepare Repository

### 1.1 Required Files

Make sure your repository has these files:


**`pyproject.toml`** (dependencies managed by uv):
```toml
[project]
name = "jeopardy"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "flask",
    "flask-sqlalchemy",
    "gunicorn",
    "pillow",
]
```

**`Dockerfile`**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

# Run with gunicorn (shell form to expand $PORT)
CMD uv run gunicorn --bind 0.0.0.0:$PORT "app:create_app()"
```

### 1.2 Configure for Persistent Volume

Update your Flask config to use Railway's volume mount path:

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ['SECRET_KEY']
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    
    # Use Railway volume path
    DATA_DIR = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '/data')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR}/jeopardy.db"
    UPLOAD_FOLDER = f"{DATA_DIR}/uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
```

---

## Part 2: Deploy to Railway

### 2.1 Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Login" → "Login with GitHub"
3. Authorize Railway

### 2.2 Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Select your jeopardy repository
4. Click "Deploy Now"

Railway will automatically detect Python and start building.

### 2.3 Add Environment Variables

1. Click on your deployed service
2. Go to "Variables" tab
3. Add the following:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | (generate random: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |

### 2.4 Add Persistent Volume

This keeps your SQLite database and uploaded images safe across deploys:

1. Click on your service
2. Go to "Volumes" tab
3. Click "Add Volume"
4. Set mount path: `/data`
5. Click "Add"

Railway will redeploy with the volume attached.

### 2.5 Get Your Public URL

1. Go to "Settings" tab
2. Under "Networking", click "Generate Domain"
3. You'll get a URL like: `jeopardy-production-abc123.up.railway.app`

Save this URL - you'll need it for Telegram!

---

## Part 3: Configure Telegram Bot

### 3.1 Set Web App URL

1. Open Telegram, go to @BotFather
2. Send `/mybots`
3. Select `@svoya_jeopardy_bot`
4. Select "Bot Settings"
5. Select "Menu Button" → "Configure menu button"
6. Enter your Railway URL: `https://your-app.up.railway.app`
7. Enter button text: `🎮 Play Jeopardy`

### 3.2 Register Webhook

Set up the webhook so your bot receives updates when added to groups:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.up.railway.app/webhook"}'
```

Verify it's set:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 3.3 Test the Mini App

1. Open Telegram
2. Add your bot to a group chat (you'll become the host)
3. Tap the menu button to open the Mini App
4. You should see the game interface!

---

## Part 4: Auto-Deploy Setup

Railway automatically deploys when you push to your connected branch (usually `main`).

### Workflow

1. Make changes locally
2. `git push origin main`
3. Railway detects the push and redeploys (~1-2 minutes)
4. Your changes are live!

### View Deploy Logs

1. Go to Railway dashboard
2. Click your service
3. Click "Deployments" tab
4. Click any deployment to see logs

---

## Part 5: Maintenance

### View Application Logs

1. Go to Railway dashboard
2. Click your service
3. Click "Logs" tab (real-time logs)

### Restart Application

1. Go to Railway dashboard
2. Click your service
3. Click "Deployments" tab
4. Click "Redeploy" on the latest deployment

### Access Database (if needed)

You can connect to your app's shell:

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Link project: `railway link`
4. Open shell: `railway shell`
5. Access SQLite: `sqlite3 /data/jeopardy.db`

### Backup Database

```bash
# Using Railway CLI
railway run cat /data/jeopardy.db > backup.db
```

---

## Part 6: Troubleshooting

### App Not Loading

1. Check deployment logs in Railway dashboard
2. Look for Python errors in the "Logs" tab
3. Verify environment variables are set

### Webhook Not Working

```bash
# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Re-register if needed
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d '{"url": "https://your-app.up.railway.app/webhook"}'
```

### Images Not Persisting

Make sure:
1. Volume is attached (check "Volumes" tab)
2. App is saving to `/data/uploads` (the volume mount path)
3. `RAILWAY_VOLUME_MOUNT_PATH` env var is set automatically by Railway

### Database Reset

If you need to start fresh:

```bash
railway shell
rm /data/jeopardy.db
exit
# Redeploy to recreate database
```

---

## Quick Reference

| Task | How |
|------|-----|
| View logs | Railway Dashboard → Service → Logs |
| Redeploy | Railway Dashboard → Deployments → Redeploy |
| Add env var | Railway Dashboard → Variables → Add |
| View URL | Railway Dashboard → Settings → Domains |
| CLI shell | `railway shell` |

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `abc123...` (random hex) |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | `123456:ABC-DEF...` |
| `RAILWAY_VOLUME_MOUNT_PATH` | Auto-set by Railway | `/data` |
