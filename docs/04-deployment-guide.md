# Deployment Guide: New Year Jeopardy Party Game

## Overview

We'll deploy to **Fly.io**, which provides:
- Free HTTPS subdomain (`*.fly.dev`)
- Auto-deploy with GitHub Actions (optional)
- Persistent volumes for SQLite and uploaded images
- Global edge deployment
- Automatic SSL certificates

**Total deployment time: ~20 minutes**

---

## Prerequisites

- Fly.io account (free, sign up at [fly.io](https://fly.io))
- Fly CLI installed (`flyctl`)
- Telegram Bot token (from @BotFather)

---

## Part 1: Install Fly CLI

### macOS

```bash
brew install flyctl
```

### Linux

```bash
curl -L https://fly.io/install.sh | sh
```

### Windows

```powershell
pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

After installation, log in:

```bash
fly auth login
```

---

## Part 2: Deploy to Fly.io

### 2.1 Navigate to Project Directory

```bash
cd jeopardy
```

### 2.2 Launch the App

Run the launch command (this will use the existing `fly.toml`):

```bash
fly launch --no-deploy
```

When prompted:
- **App name**: Choose a unique name (e.g., `my-jeopardy-game`) or accept the generated one
- **Region**: Select the region closest to your users (e.g., `ams` for Amsterdam, `lhr` for London)
- **Would you like to set up a PostgreSQL database?**: No
- **Would you like to set up Redis?**: No

### 2.3 Create Persistent Volume

Create a volume for the SQLite database and uploaded images:

```bash
fly volumes create jeopardy_data --region ams --size 1
```

> **Note**: Replace `ams` with your chosen region. The volume name `jeopardy_data` must match the `source` in `fly.toml`.

### 2.4 Set Environment Variables (Secrets)

```bash
# Generate a secure secret key
fly secrets set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Set your Telegram bot token
fly secrets set TELEGRAM_BOT_TOKEN="your-bot-token-here"
```

> **Note**: The `APP_URL` is automatically derived from your Fly.io app name (e.g., `https://your-app-name.fly.dev`). You only need to set it manually if using a custom domain:
> ```bash
> fly secrets set APP_URL="https://your-custom-domain.com"
> ```

### 2.5 Deploy the App

```bash
fly deploy
```

This will:
1. Build the Docker image
2. Push it to Fly.io's registry
3. Deploy to your selected region
4. Mount the persistent volume

### 2.6 Get Your Public URL

After deployment, get your app URL:

```bash
fly status
```

Your app will be available at: `https://your-app-name.fly.dev`

---

## Part 3: Configure Telegram Bot

### 3.1 Set Web App URL

1. Open Telegram, go to @BotFather
2. Send `/mybots`
3. Select your bot
4. Select "Bot Settings"
5. Select "Menu Button" → "Configure menu button"
6. Enter your Fly.io URL: `https://your-app-name.fly.dev`
7. Enter button text: `🎮 Play Jeopardy`

### 3.2 Register Webhook

Set up the webhook so your bot receives updates:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app-name.fly.dev/webhook"}'
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

## Part 4: Auto-Deploy with GitHub Actions (Optional)

### 4.1 Get Fly.io API Token

```bash
fly tokens create deploy -x 999999h
```

Copy the token output.

### 4.2 Add GitHub Secret

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `FLY_API_TOKEN`
5. Value: Paste your token

### 4.3 Create GitHub Actions Workflow

Create `.github/workflows/fly.yml`:

```yaml
name: Fly Deploy
on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        working-directory: ./jeopardy
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Now every push to `main` will automatically deploy!

---

## Part 5: Maintenance

### View Application Logs

```bash
fly logs
```

Or stream logs in real-time:

```bash
fly logs --app your-app-name
```

### Check App Status

```bash
fly status
```

### Restart Application

```bash
fly apps restart
```

### SSH into the Machine

```bash
fly ssh console
```

### Access Database

```bash
fly ssh console -C "sqlite3 /data/data/jeopardy.db"
```

### Backup Database

```bash
# Download the database file
fly ssh sftp get /data/data/jeopardy.db ./backup.db
```

### Scale the App

```bash
# Scale to 2 machines
fly scale count 2

# Change VM size
fly scale vm shared-cpu-2x
```

---

## Part 6: Troubleshooting

### App Not Loading

1. Check logs: `fly logs`
2. Check status: `fly status`
3. Verify secrets are set: `fly secrets list`

### Webhook Not Working

```bash
# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Re-register if needed
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d '{"url": "https://your-app-name.fly.dev/webhook"}'
```

### Volume Issues

```bash
# List volumes
fly volumes list

# Check volume is attached
fly status
```

### Database Reset

If you need to start fresh:

```bash
fly ssh console
rm /data/data/jeopardy.db
exit
fly apps restart
```

### Deploy Failures

```bash
# View recent deployments
fly releases

# View specific release
fly releases show v1
```

---

## Quick Reference

| Task | Command |
|------|---------|
| View logs | `fly logs` |
| App status | `fly status` |
| Deploy | `fly deploy` |
| Restart | `fly apps restart` |
| SSH access | `fly ssh console` |
| List secrets | `fly secrets list` |
| Set secret | `fly secrets set KEY=value` |
| Scale | `fly scale count N` |

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `abc123...` (random hex) |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | `123456:ABC-DEF...` |
| `FLY_APP_NAME` | Auto-set by Fly.io | `my-jeopardy-game` |
| `FLY_VOLUME_PATH` | Volume mount path (default `/data`) | `/data` |

---

## Cost Estimation

Fly.io's free tier includes:
- 3 shared-cpu-1x VMs (256MB RAM each)
- 3GB persistent storage total
- 160GB outbound bandwidth

For a small party game app, you'll likely stay within the free tier.

Paid usage (if needed):
- Shared CPU: ~$1.94/month per 256MB VM
- Volumes: ~$0.15/GB/month
- Bandwidth: $0.02/GB after free tier

---

## Comparison: Fly.io vs Railway

| Feature | Fly.io | Railway |
|---------|--------|---------|
| Free tier | ✅ Generous | ⚠️ Limited for apps |
| Persistent storage | ✅ Volumes | ✅ Volumes |
| Auto HTTPS | ✅ | ✅ |
| Global regions | ✅ 30+ regions | ✅ Limited |
| CLI | ✅ Excellent | ✅ Good |
| GitHub integration | ✅ Actions | ✅ Native |
| Container support | ✅ Native | ✅ Native |
