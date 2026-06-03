# PostgreSQL Setup Guide for WebLift Production

## Overview
This guide covers installing PostgreSQL and migrating from SQLite for production deployment.

---

## Step 1: Install PostgreSQL

### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
sudo systemctl status postgresql
```

### CentOS/RHEL/Fedora
```bash
# Install PostgreSQL
sudo dnf install postgresql-server postgresql-contrib

# Initialize database
sudo postgresql-setup --initdb

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS (with Homebrew)
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL
brew services start postgresql
```

### Windows
1. Download installer from https://www.postgresql.org/download/windows/
2. Run installer with default settings
3. Remember the password you set for postgres user
4. Add `C:\Program Files\PostgreSQL\XX\bin` to PATH

---

## Step 2: Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database
CREATE DATABASE weblift_prod;

# Create user with secure password
CREATE USER weblift_user WITH PASSWORD 'your-secure-password-here';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE weblift_prod TO weblift_user;

# Exit
\q
```

### Secure the PostgreSQL User

```bash
# Set connection limit (optional, for resource control)
sudo -u postgres psql -c "ALTER USER weblift_user WITH CONNECTION LIMIT 100;"
```

---

## Step 3: Configure PostgreSQL

### Edit PostgreSQL Configuration

```bash
# Find configuration file location
sudo -u postgres psql -c "SHOW config_file;"

# Typically: /etc/postgresql/14/main/postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf
```

### Recommended Production Settings

```conf
# Memory Settings (adjust based on your RAM)
shared_buffers = 256MB                  # 25% of RAM
effective_cache_size = 1GB              # 50% of RAM
work_mem = 4MB                        # Per connection
maintenance_work_mem = 64MB

# Connection Settings
max_connections = 200
listen_addresses = 'localhost'          # Change to '*' for remote (with firewall!)

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000       # Log slow queries (>1s)

# Performance
random_page_cost = 1.1                 # For SSD storage
effective_io_concurrency = 200
```

### Configure Client Authentication

```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Ensure these lines exist:
```conf
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
```

### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

---

## Step 4: Update Django Environment

### Edit `.env` File

```bash
# Database Configuration
USE_SQLITE=false
DB_NAME=weblift_prod
DB_USER=weblift_user
DB_PASSWORD=your-secure-password-here
DB_HOST=localhost
DB_PORT=5432
```

### Install psycopg2

```bash
# Activate virtual environment
source venv/bin/activate

# Install PostgreSQL adapter
pip install psycopg2-binary

# Or for production (requires PostgreSQL dev libraries):
# sudo apt install libpq-dev
# pip install psycopg2
```

---

## Step 5: Migrate Data from SQLite

### Option A: Fresh Start (Recommended for Production)

```bash
# Just run migrations on empty PostgreSQL database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Option B: Migrate Existing Data

```bash
# 1. Ensure SQLite database is up to date
python manage.py migrate --database=default

# 2. Dump data from SQLite
python manage.py dumpdata --all --indent 2 > datadump.json

# 3. Switch to PostgreSQL in settings/.env
# Edit .env: USE_SQLITE=false

# 4. Create PostgreSQL tables
python manage.py migrate

# 5. Load data (exclude contenttypes to avoid conflicts)
python manage.py loaddata datadump.json
```

**Note:** If you get contenttypes errors:
```bash
# Dump excluding contenttypes and auth permissions
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > datadump.json
```

---

## Step 6: Verify Installation

### Test Django Connection

```bash
# Check deployment readiness
python manage.py check --deploy

# Verify database connection
python manage.py dbshell

# Should open PostgreSQL shell
\conninfo
\q
```

### Run Tests

```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test subscriptions
```

### Verify Indexes

```bash
# Connect to PostgreSQL
sudo -u postgres psql weblift_prod

# List tables
\dt

# Check indexes on main tables
\di subscriptions_*
\di keyword_ai_*
```

---

## Step 7: Production Hardening

### Enable SSL Connections

```bash
# Generate SSL certificates (or use Let's Encrypt)
sudo mkdir /etc/postgresql/14/main/ssl
sudo openssl req -new -x509 -days 365 -nodes -text \
  -out /etc/postgresql/14/main/ssl/server.crt \
  -keyout /etc/postgresql/14/main/ssl/server.key \
  -subj "/CN=your-domain.com"

sudo chmod 600 /etc/postgresql/14/main/ssl/server.key
sudo chown postgres:postgres /etc/postgresql/14/main/ssl/*
```

Update `postgresql.conf`:
```conf
ssl = on
ssl_cert_file = '/etc/postgresql/14/main/ssl/server.crt'
ssl_key_file = '/etc/postgresql/14/main/ssl/server.key'
```

### Set Up Backups

```bash
# Create backup script
sudo nano /usr/local/bin/backup-weblift.sh
```

```bash
#!/bin/bash
# Backup script for WebLift PostgreSQL database

BACKUP_DIR="/var/backups/weblift"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="weblift_prod"
RETENTION_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Full backup
pg_dump -Fc -Z9 $DB_NAME > "$BACKUP_DIR/weblift_${DATE}.dump"

# Delete old backups
find $BACKUP_DIR -name "weblift_*.dump" -mtime +$RETENTION_DAYS -delete

# Log backup
echo "[$(date)] Backup completed: weblift_${DATE}.dump" >> /var/log/weblift-backup.log
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-weblift.sh

# Test backup
sudo -u postgres /usr/local/bin/backup-weblift.sh

# Schedule daily backups
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-weblift.sh
```

### Test Restore Procedure

```bash
# Test restore on staging database
createdb weblift_test
pg_restore -d weblift_test /var/backups/weblift/weblift_20260115_020000.dump
```

---

## Step 8: Monitoring Setup

### Enable PostgreSQL Statistics

```bash
sudo -u postgres psql
```

```sql
-- Enable query statistics extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Update `postgresql.conf`:
```conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000
```

### Useful Monitoring Queries

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check port
sudo ss -tlnp | grep 5432

# Check pg_hba.conf allows your connection
sudo cat /etc/postgresql/14/main/pg_hba.conf
```

### Permission Denied

```bash
# Reset user password if needed
sudo -u postgres psql -c "ALTER USER weblift_user WITH PASSWORD 'newpassword';"

# Verify database ownership
sudo -u postgres psql -c "\l"
```

### Migration Errors

```bash
# If migration fails, try:
python manage.py migrate --fake-initial

# Or reset migrations for specific app:
python manage.py migrate subscriptions zero
python manage.py migrate subscriptions
```

### Performance Issues

```bash
# Analyze tables for query planner
sudo -u postgres psql weblift_prod -c "ANALYZE;"

# Vacuum database
sudo -u postgres psql weblift_prod -c "VACUUM ANALYZE;"
```

---

## Next Steps

After PostgreSQL is configured:

1. **Run Django Migrations**
   ```bash
   python manage.py migrate
   ```

2. **Collect Static Files**
   ```bash
   python manage.py collectstatic
   ```

3. **Start Celery Workers** (Redis required)
   ```bash
   celery -A Project worker -l info
   ```

4. **Deploy with Production Server**
   ```bash
   gunicorn Project.wsgi:application --bind 0.0.0.0:8000
   ```

5. **Verify with Health Check**
   ```bash
   curl http://localhost:8000/health/
   ```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `sudo -u postgres psql` | Open PostgreSQL shell |
| `\l` | List databases |
| `\c weblift_prod` | Connect to database |
| `\dt` | List tables |
| `\di` | List indexes |
| `\q` | Quit |
| `pg_dump -Fc dbname > file.dump` | Backup database |
| `pg_restore -d dbname file.dump` | Restore database |

---

## Security Checklist

- [ ] PostgreSQL password is strong (>20 chars)
- [ ] pg_hba.conf only allows necessary connections
- [ ] SSL is enabled
- [ ] Database user has minimal privileges
- [ ] Backups are encrypted (if sensitive data)
- [ ] Backups tested monthly
- [ ] Database logs are monitored
- [ ] Firewall blocks port 5432 from external access (if not needed)
