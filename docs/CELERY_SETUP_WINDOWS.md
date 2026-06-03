# Celery Setup Guide for Windows

## Overview
Celery is a distributed task queue for running background jobs asynchronously. Essential for WebLift's heavy operations like SEO audits and competitor analysis.

---

## Prerequisites

- Redis installed and running (see REDIS_SETUP_WINDOWS.md)
- Python virtual environment activated

---

## Step 1: Install Celery

```powershell
# In your project directory with venv activated
pip install celery redis

# For Windows eventlet pool (recommended for Windows)
pip install eventlet

# Or use gevent alternative
pip install gevent
```

---

## Step 2: Update .env Configuration

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
USE_CELERY=true
```

---

## Step 3: Verify Celery Configuration

Test that Django can connect to Celery:

```powershell
python -c "from Project.celery import app; print('Celery app loaded successfully')"
```

If you see the success message, Celery is configured correctly.

---

## Step 4: Start Celery Worker

### Option A: Using eventlet (Recommended for Windows)

```powershell
# In one terminal, start the worker
celery -A Project worker -l info -P eventlet

# For production with more workers
celery -A Project worker -l info -P eventlet --concurrency=4
```

### Option B: Using solo pool (Simple, single-threaded)

```powershell
celery -A Project worker -l info -P solo
```

### Option C: Using gevent

```powershell
celery -A Project worker -l info -P gevent --concurrency=4
```

**Note**: Default prefork pool doesn't work well on Windows. Always use `-P eventlet`, `-P solo`, or `-P gevent`.

---

## Step 5: Start Celery Beat (Scheduler)

For periodic tasks:

```powershell
# In another terminal
celery -A Project beat -l info

# Or run worker + beat together
celery -A Project worker -l info -P eventlet --beat
```

---

## Step 6: Test Celery Tasks

### Test in Django Shell

```powershell
python manage.py shell
```

```python
from keyword_ai.tasks import cleanup_old_tasks

# Run task synchronously (for testing)
result = cleanup_old_tasks()
print(f"Cleaned up {result} old tasks")

# Run task asynchronously (normal usage)
result = cleanup_old_tasks.delay()
print(f"Task ID: {result.id}")

# Check task status
result.status
result.ready()
result.get(timeout=10)  # Wait for result
```

---

## Step 7: Production Configuration

### Run Celery as Windows Service

Create a batch file `start_celery.bat`:

```batch
@echo off
cd /d E:\Project
call .\venv\Scripts\activate
celery -A Project worker -l info -P eventlet --concurrency=4
```

Create another `start_beat.bat`:

```batch
@echo off
cd /d E:\Project
call .\venv\Scripts\activate
celery -A Project beat -l info
```

### Using Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task → Name: "WebLift Celery Worker"
3. Trigger: When computer starts
4. Action: Start a program
5. Program: `E:\Project\venv\Scripts\celery.exe`
6. Arguments: `-A Project worker -l info -P eventlet --concurrency=4`
7. Start in: `E:\Project`

---

## Monitoring Tasks

### Flower (Web-based monitoring)

```powershell
pip install flower

# Start Flower dashboard
celery -A Project flower --port=5555

# Access at http://localhost:5555
```

### Command Line Monitoring

```powershell
# List active workers
celery -A Project inspect active

# List scheduled tasks
celery -A Project inspect scheduled

# List registered tasks
celery -A Project inspect registered
```

---

## Troubleshooting

### "Error: Can't pickle <function>"

Windows + Celery + Pickle = Problems. Use JSON serializer:

```python
# In celery.py
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
```

### "ModuleNotFoundError" or Import Errors

```powershell
# Ensure you're in the project directory
cd E:\Project

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Make sure Project is in PYTHONPATH
$env:PYTHONPATH = "E:\Project;$env:PYTHONPATH"
```

### "Connection refused" to Redis

```powershell
# Check Redis is running
redis-cli ping

# Should return: PONG

# If not, start Redis
Start-Service redis
```

### Worker Hangs or Freezes

```powershell
# Use solo pool for debugging
celery -A Project worker -l debug -P solo

# Clear task queue if stuck
redis-cli FLUSHDB
```

### Database Connection Issues

Celery workers need their own database connections. If you get:
"DatabaseWrapper objects created in a thread can only be used in that same thread"

Add to `celery.py`:

```python
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

---

## Performance Tuning

### Worker Concurrency

```powershell
# Auto-detect CPU cores
celery -A Project worker -l info -P eventlet --concurrency=auto

# Or set manually based on CPU cores
celery -A Project worker -l info -P eventlet --concurrency=4
```

### Task Time Limits

Add to settings.py:

```python
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes warning
```

### Prefetch Multiplier

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # For long tasks
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `celery -A Project worker -l info -P eventlet` | Start worker with eventlet |
| `celery -A Project beat -l info` | Start scheduler |
| `celery -A Project flower` | Start monitoring dashboard |
| `celery -A Project inspect active` | Show active tasks |
| `celery -A Project purge` | Clear all pending tasks |
| `redis-cli FLUSHDB` | Clear all Celery data |

---

## Next Steps

After Celery is running:

1. **Test async tasks** with `cleanup_old_tasks.delay()`
2. **Monitor Flower** at http://localhost:5555
3. **Optimize heavy views** to use `.delay()`
4. **Set up error tracking** with Sentry for failed tasks

---

## Production Checklist

- [ ] Celery workers running as Windows service
- [ ] Redis has persistence configured
- [ ] Task time limits set appropriately
- [ ] Error monitoring configured (Sentry)
- [ ] Worker concurrency optimized for server
- [ ] Beat scheduler running for periodic tasks
- [ ] Task results backend configured (Redis)
- [ ] Flower dashboard secured (add auth)
