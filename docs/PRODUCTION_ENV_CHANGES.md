# Production .env Changes Required

## ⚠️ CRITICAL: API Key Rotation Required
Your previous `.env` file contained exposed API keys. **Rotate these immediately:**

1. **Groq API Key** - Generate new at https://console.groq.com
2. **Moz API Credentials** - Generate new at https://moz.com/products/api
3. **PageSpeed API Key** - Generate new at https://developers.google.com/speed/docs/insights/v5/get-started
4. **Pinecone API Key** - Generate new at https://app.pinecone.io

---

## Required Changes for Production

### 1. Django Core Settings

| Setting | Current (Dev) | Production |
|---------|--------------|------------|
| `DJANGO_SECRET_KEY` | `django-insecure-...` | Generate new 50+ char random string |
| `DEBUG` | `True` | `false` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `yourdomain.com,www.yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | `http://...` | `https://yourdomain.com,https://www.yourdomain.com` |

### 2. Database (Switch to PostgreSQL)

**Remove:**
```
USE_SQLITE=true
```

**Add:**
```
USE_SQLITE=false
DB_NAME=weblift_prod
DB_USER=weblift_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Redis Caching (Enable)

**Change:**
```
USE_REDIS_CACHE=false
→
USE_REDIS_CACHE=true
REDIS_URL=redis://127.0.0.1:6379/1
```

### 4. Celery (Switch to Redis)

**Change:**
```
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
CELERY_TASK_ALWAYS_EAGER=true
→
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
# Remove CELERY_TASK_ALWAYS_EAGER line
```

### 5. SSL & Security (Add These)

```
SSL_VERIFY_MODE=strict
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
```

### 6. Email (Configure SMTP)

```
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=WebLift <noreply@yourdomain.com>
```

---

## Files Created

1. **`.env.production.template`** - Complete production-ready template
2. **`PRODUCTION_ENV_CHANGES.md`** - This file

---

## Deployment Commands

After updating your `.env` file:

```bash
# 1. Check deployment readiness
python manage.py check --deploy

# 2. Run database migrations
python manage.py migrate

# 3. Collect static files
python manage.py collectstatic

# 4. Test the application
python manage.py test

# 5. Start with production server
gunicorn Project.wsgi:application --bind 0.0.0.0:8000
```

---

## Security Reminders

- [ ] Rotate all API keys (they were exposed)
- [ ] Set `.env` file permissions: `chmod 600 .env`
- [ ] Never commit `.env` to git
- [ ] Use HTTPS only in production
- [ ] Configure firewall (only ports 80, 443, 22 open)
- [ ] Enable automatic security updates
