# 🚂 Railway Deployment Guide

This guide walks you through deploying WebLift to Railway.

## ✅ Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Account**: Your code should be in a GitHub repository
3. **Required API Keys**:
   - Django Secret Key
   - Groq API Key (for AI features)
   - Pinecone API Key (for vector search)

---

## 🚀 Quick Deploy (5 minutes)

### Step 1: Create Project on Railway

```bash
# Install Railway CLI (optional, but recommended)
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

Or use the **Railway Dashboard**:
1. Go to [railway.app/dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your repository

---

### Step 2: Add PostgreSQL Database

1. In your Railway project dashboard, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway automatically creates a PostgreSQL instance and sets `DATABASE_URL`
3. No configuration needed - Django will auto-detect it!

---

### Step 3: Configure Environment Variables

In Railway dashboard, go to your service → **"Variables"** tab, add these:

#### Required Variables

| Variable | Description | How to Get |
|----------|-------------|------------|
| `DJANGO_SECRET_KEY` | Django security key | `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'` |
| `DEBUG` | Set to `false` for production | `false` |
| `ALLOWED_HOSTS` | Your Railway domain | `${RAILWAY_STATIC_URL}` |

#### API Keys (Required for AI features)

| Variable | Description | Get From |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq LLM API | [console.groq.com](https://console.groq.com) |
| `PINECONE_API_KEY` | Vector database | [app.pinecone.io](https://app.pinecone.io) |
| `PINECONE_INDEX_NAME` | Pinecone index | Your Pinecone dashboard |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | - | Error tracking (get from sentry.io) |
| `USE_GROQ` | `true` | Use Groq for AI |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model |

---

### Step 4: Deploy!

Railway automatically deploys when you push to GitHub.

**Manual deploy:**
```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

---

## 🔍 Verify Deployment

### 1. Check Health Endpoint
```bash
curl https://your-app.railway.app/health/
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "application": "ok"
  }
}
```

### 2. Check Readiness
```bash
curl https://your-app.railway.app/ready/
```

### 3. View Logs
In Railway dashboard → **"Deployments"** → Click on deployment → **"Logs"**

---

## 🛠️ Troubleshooting

### Issue: "Module not found" errors

**Fix**: Ensure all dependencies are in `requirements.txt`:
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update requirements"
git push
```

### Issue: Static files not loading (404)

**Fix**: WhiteNoise is already configured. Check logs:
- Ensure `collectstatic` ran during build
- Check `railway.json` has correct build commands

### Issue: Database connection failed

**Fix**: 
1. Verify PostgreSQL is provisioned
2. Check `DATABASE_URL` is set automatically
3. Ensure migrations ran: Check deploy logs

### Issue: "DisallowedHost" error

**Fix**: Update `ALLOWED_HOSTS` variable:
```
ALLOWED_HOSTS=${RAILWAY_STATIC_URL},your-custom-domain.com
```

### Issue: 502 Bad Gateway

**Fix**: 
- Check app is binding to `$PORT`
- Verify Gunicorn is running: Check logs for "Listening on"
- Health check endpoint should return 200

---

## 📊 Scaling

### Vertical Scaling (More Power)
1. Railway Dashboard → Service → **"Settings"**
2. Increase vCPU and Memory

### Horizontal Scaling (More Instances)
Railway automatically handles this based on traffic.

---

## 🔐 Security Checklist

Before going live:

- [ ] `DEBUG=false` in production
- [ ] `DJANGO_SECRET_KEY` is strong and unique
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] HTTPS enforced (Railway provides SSL)
- [ ] API keys stored in Railway variables (not code)
- [ ] Sentry configured for error tracking

---

## 🌐 Custom Domain

1. Railway Dashboard → Service → **"Settings"** → **"Domains"**
2. Click **"Generate Domain"** or add custom domain
3. Update `ALLOWED_HOSTS` with your domain
4. Update `CSRF_TRUSTED_ORIGINS`:
   ```
   CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
   ```

---

## 📁 Files Created for Railway

| File | Purpose |
|------|---------|
| `Procfile` | Defines web process and release commands |
| `nixpacks.toml` | Build configuration for Railway |
| `railway.json` | Deployment settings & health checks |
| `requirements.txt` | Includes `dj-database-url` for Railway DB |

---

## 🆘 Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Django on Railway**: [docs.railway.app/guides/django](https://docs.railway.app/guides/django)
- **Logs**: Railway Dashboard → Deployments → Logs

---

## ✨ You're Ready!

Your WebLift application is now production-ready on Railway with:
- ✅ Auto-scaling
- ✅ Managed PostgreSQL
- ✅ SSL/HTTPS
- ✅ Health checks
- ✅ Zero-downtime deploys

**Next**: Set up monitoring with Sentry and configure your custom domain!
