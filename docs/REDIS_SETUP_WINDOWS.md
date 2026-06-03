# Redis Setup Guide for Windows

## Overview
Redis is an in-memory data store used for caching, session storage, and Celery task queuing in WebLift.

---

## Step 1: Download Redis for Windows

### Option A: Official Redis (Recommended for Production)

**Note:** Redis doesn't officially support Windows, but Microsoft maintains a port.

1. **Download Memurai** (Redis-compatible for Windows, free for development):
   - https://www.memurai.com/ (free tier available)
   
2. **Or use WSL2** (Windows Subsystem for Linux):
   ```powershell
   # Install WSL2 with Ubuntu
   wsl --install -d Ubuntu
   # Restart computer, then in Ubuntu:
   sudo apt update
   sudo apt install redis-server
   sudo service redis-server start
   ```

### Option B: Redis for Windows (Microsoft Archive)

1. Download from GitHub releases:
   - https://github.com/microsoftarchive/redis/releases
   - Download `Redis-x64-3.0.504.msi` (or latest)

2. Run the installer
3. Redis will be installed as a Windows service

### Option C: Using Chocolatey

```powershell
# Run as Administrator
choco install redis-64
```

---

## Step 2: Start Redis Service

### If installed via MSI (Microsoft Archive)

Redis runs automatically as a service. Check status:
```powershell
Get-Service redis
```

If not running:
```powershell
Start-Service redis
```

### If using WSL2

```bash
# In Ubuntu terminal
sudo service redis-server start
sudo service redis-server status
```

### Test Redis Connection

```powershell
# Using redis-cli (if in PATH)
redis-cli ping
# Should return: PONG

# Or using Python
python -c "import redis; r = redis.Redis(); print(r.ping())"
```

---

## Step 3: Configure Django for Redis

### Install Redis Python Client

```powershell
pip install redis django-redis
```

### Update .env File

```env
# Redis Configuration
USE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # Leave empty if no password
```

---

## Step 4: Redis Configuration Options

### Basic Configuration (C:\Program Files\Redis\redis.windows.conf)

```conf
# Memory settings
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (optional for cache-only)
save ""  # Disable RDB snapshots for pure caching

# Security (if needed)
# requirepass your-secure-password

# Bind to localhost only (secure)
bind 127.0.0.1

# Disable protected mode for local development
protected-mode no
```

Restart Redis after changes:
```powershell
Restart-Service redis
```

---

## Step 5: Verify Redis is Working

### Test with Django

```powershell
python manage.py shell
```

```python
from django.core.cache import cache

# Test cache
 cache.set('test_key', 'hello', 30)
value = cache.get('test_key')
print(value)  # Should print: hello

# Test with large data
import time
start = time.time()
for i in range(1000):
    cache.set(f'key_{i}', f'value_{i}', 60)
print(f"Set 1000 keys in {time.time() - start:.2f}s")
```

### Monitor Redis in Real-time

```powershell
redis-cli monitor
```

---

## Step 6: Redis as Session Backend (Optional)

For better scalability, store sessions in Redis instead of database:

### Update settings.py

```python
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
```

---

## Troubleshooting

### "redis-cli is not recognized"

```powershell
# Add Redis to PATH temporarily
$env:Path += ";C:\Program Files\Redis"

# Or permanently (run as Administrator)
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\Redis",
    "Machine"
)
```

### Connection Refused

```powershell
# Check if Redis is running
Get-Service redis

# Check port
netstat -an | findstr 6379

# Check Redis logs
Get-Content "C:\Program Files\Redis\Logs\redis_log.txt" -Tail 20
```

### Memory Issues

```powershell
# Check Redis memory usage
redis-cli info memory

# Clear all cache (DANGER: only in development)
redis-cli flushall
```

### WSL2 Specific Issues

```bash
# If Redis won't start in WSL2
sudo mkdir -p /var/run/redis
sudo chown redis:redis /var/run/redis
sudo service redis-server start
```

---

## Redis Commands Quick Reference

| Command | Description |
|---------|-------------|
| `redis-cli ping` | Test connection |
| `redis-cli info` | Server info |
| `redis-cli info memory` | Memory usage |
| `redis-cli keys '*'` | List all keys |
| `redis-cli flushall` | Delete all keys |
| `redis-cli monitor` | Real-time monitoring |
| `redis-cli dbsize` | Count keys in DB |

---

## Production Checklist

- [ ] Redis bound to localhost only (or secure network)
- [ ] Authentication enabled (requirepass) if exposed
- [ ] Memory limits configured (maxmemory)
- [ ] Eviction policy set (maxmemory-policy)
- [ ] Persistence configured (if needed)
- [ ] Monitoring/alerting set up
- [ ] Redis runs as limited user (not Administrator)

---

## Next Steps

After Redis is configured:

1. **Update Django cache settings** (done in Phase 3)
2. **Restart Django server**
3. **Test caching** with `python manage.py shell`
4. **Monitor cache hit rates** with `redis-cli info stats`
