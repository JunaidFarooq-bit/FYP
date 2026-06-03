# PostgreSQL Setup Guide for Windows

## Overview
Windows-specific guide for installing PostgreSQL and migrating from SQLite.

---

## Step 1: Download and Install PostgreSQL

### Option A: Official Installer (Recommended)

1. **Download PostgreSQL**
   - Go to: https://www.postgresql.org/download/windows/
   - Click "Download the installer"
   - Download PostgreSQL 15.x or 16.x for Windows x86-64

2. **Run the Installer**
   - Double-click the downloaded `.exe` file
   - Click "Next" through the welcome screen
   - **Installation Directory**: Keep default (`C:\Program Files\PostgreSQL\16`)
   - **Select Components**: Check all (PostgreSQL Server, pgAdmin, Stack Builder, Command Line Tools)
   - **Data Directory**: Keep default (`C:\Program Files\PostgreSQL\16\data`)
   - **Password**: Set a strong password for `postgres` user (remember this!)
   - **Port**: Keep default `5432`
   - **Locale**: Keep default or select your region
   - Click "Next" and wait for installation

3. **Skip Stack Builder** (unless you need additional tools)
   - When prompted, you can skip Stack Builder

### Option B: Using Chocolatey (Package Manager)

If you have Chocolatey installed:

```powershell
# Run as Administrator
choco install postgresql
```

---

## Step 2: Add PostgreSQL to System PATH

This lets you use `psql` and other commands from anywhere.

### Method 1: Through System Settings

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Click "Advanced" tab → "Environment Variables"
3. Under "System variables", find `Path` → Click "Edit"
4. Click "New" and add:
   ```
   C:\Program Files\PostgreSQL\16\bin
   ```
5. Click "OK" on all dialogs

### Method 2: PowerShell (One-liner)

```powershell
# Run as Administrator
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\PostgreSQL\16\bin",
    "Machine"
)
```

### Method 3: Temporarily (Current Session Only)

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
```

---

## Step 3: Create Database and User

### Using psql (Command Line)

Open **Command Prompt** or **PowerShell** as Administrator:

```cmd
# Connect as postgres user
psql -U postgres

# Enter the password you set during installation
```

Once in psql:

```sql
-- Create database
CREATE DATABASE weblift_prod;

-- Create user with secure password
CREATE USER weblift_user WITH PASSWORD 'your-secure-password-here-min-20-chars';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE weblift_prod TO weblift_user;

-- Make user able to create schemas (needed for migrations)
ALTER DATABASE weblift_prod OWNER TO weblift_user;

-- Exit
\q
```

### Alternative: Using pgAdmin (GUI)

1. Open **pgAdmin 4** from Start Menu
2. Connect to server (double-click "PostgreSQL 16")
3. Enter postgres password when prompted
4. Right-click "Databases" → "Create" → "Database"
   - Database: `weblift_prod`
   - Owner: `postgres` (we'll change it)
5. Right-click "Login/Group Roles" → "Create" → "Login/Group Role"
   - General tab:
     - Name: `weblift_user`
   - Definition tab:
     - Password: `your-secure-password`
     - Password expiry: Never
   - Privileges tab:
     - Can login: Yes
     - Superuser: No
     - Create roles: No
     - Create databases: Yes
6. Right-click `weblift_prod` database → Properties
   - Owner: Select `weblift_user`

---

## Step 4: Configure PostgreSQL

### Edit postgresql.conf

1. Navigate to data directory:
   ```
   C:\Program Files\PostgreSQL\16\data\postgresql.conf
   ```

2. Open with Notepad as Administrator (or VS Code)

3. Find and modify these settings:

```conf
# Memory Settings (adjust based on your RAM)
shared_buffers = 256MB                  # 25% of RAM
effective_cache_size = 1GB              # 50% of RAM
work_mem = 4MB                        # Per connection
maintenance_work_mem = 64MB

# Connection Settings
max_connections = 200
listen_addresses = 'localhost'          # '*' for remote (with firewall!)

# Logging (Windows paths use forward slashes or double backslashes)
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

Edit `C:\Program Files\PostgreSQL\16\data\pg_hba.conf`:

Find these lines and ensure they exist:
```conf
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
```

**Important for Windows**: If you see `md5` instead of `scram-sha-256`, that's fine for local development.

### Restart PostgreSQL Service

```powershell
# Run as Administrator
Restart-Service postgresql-x64-16

# Or through Services app:
# Win + R → services.msc → Find "postgresql-x64-16" → Right-click → Restart
```

---

## Step 5: Update Django Environment

### Install psycopg2

```powershell
# Activate your virtual environment first
.\venv\Scripts\activate

# Install PostgreSQL adapter
pip install psycopg2-binary

# If that fails, you may need PostgreSQL development libraries:
# Download from https://www.postgresql.org/download/windows/ (already installed with server)
```

### Create/Update .env File

Create or update your `.env` file:

```env
# Database Configuration
USE_SQLITE=false
DB_NAME=weblift_prod
DB_USER=weblift_user
DB_PASSWORD=your-secure-password-here
DB_HOST=localhost
DB_PORT=5432
```

---

## Step 6: Migrate Data from SQLite

### Option A: Fresh Start (Recommended for Production)

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Run migrations (creates tables in PostgreSQL)
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Option B: Migrate Existing Data

```powershell
# 1. Ensure SQLite is up to date
python manage.py migrate

# 2. Dump data from SQLite
python manage.py dumpdata --all --indent 2 > datadump.json

# 3. Switch to PostgreSQL (update .env: USE_SQLITE=false)
# 4. Run migrations on PostgreSQL
python manage.py migrate

# 5. Load data
python manage.py loaddata datadump.json
```

**Fix for contenttypes errors:**
```powershell
# Dump excluding contenttypes
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > datadump.json
```

---

## Step 7: Verify Installation

### Test Django Connection

```powershell
# Check deployment readiness
python manage.py check --deploy

# Verify database connection
python manage.py dbshell

# You should see:
# psql (16.x)
# Type "help" for help.
# 
# weblift_prod=#

# Check connection info
\conninfo

# Exit
\q
```

### Verify Tables

```powershell
# Connect to database
psql -U weblift_user -d weblift_prod

# List tables (should see Django tables)
\dt

# List indexes
\di subscriptions_*
\di keyword_ai_*

# Exit
\q
```

### Run Django Tests

```powershell
python manage.py test
python manage.py test subscriptions
```

---

## Step 8: Set Up Backups on Windows

### Create Backup Script

Create file `C:\WebLift\backup.ps1`:

```powershell
# WebLift PostgreSQL Backup Script for Windows

$BackupDir = "C:\WebLift\Backups"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
$DbName = "weblift_prod"
$RetentionDays = 7

# Create backup directory if not exists
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force
}

# Full backup
$BackupFile = "$BackupDir\weblift_$Date.dump"
pg_dump -Fc -Z9 -U postgres $DbName > $BackupFile

# Log backup
$LogEntry = "[$(Get-Date)] Backup completed: weblift_$Date.dump"
Add-Content -Path "$BackupDir\backup.log" -Value $LogEntry

# Delete old backups
Get-ChildItem -Path $BackupDir -Name "weblift_*.dump" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
    Remove-Item -Force

Write-Host "Backup completed: $BackupFile"
```

### Schedule Automatic Backups (Task Scheduler)

1. Open Task Scheduler (Win + R → `taskschd.msc`)
2. Action → Create Task
3. **General** tab:
   - Name: `WebLift Database Backup`
   - Run whether user is logged on or not
   - Run with highest privileges
4. **Triggers** tab:
   - New → Daily → 2:00 AM
5. **Actions** tab:
   - New → Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\WebLift\backup.ps1"`
6. Click OK, enter credentials when prompted

---

## Windows-Specific Troubleshooting

### "psql is not recognized"

```powershell
# Add to PATH temporarily
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Or add permanently (see Step 2)
```

### Connection Refused / Could not connect

```powershell
# Check if PostgreSQL service is running
Get-Service postgresql*

# Start if not running
Start-Service postgresql-x64-16

# Check if port 5432 is listening
netstat -an | findstr 5432
```

### Permission Denied

```powershell
# Reset password (run as postgres user)
psql -U postgres -c "ALTER USER weblift_user WITH PASSWORD 'newpassword';"

# Check Windows firewall (should allow localhost)
netsh advfirewall firewall show rule name=all | findstr 5432
```

### FATAL: password authentication failed

1. Check pg_hba.conf has proper entries
2. Ensure you're using correct username/password
3. Try connecting with explicit parameters:
   ```powershell
   psql -h localhost -U weblift_user -d weblift_prod
   ```

### Django Migration Errors

```powershell
# If migration fails
python manage.py migrate --fake-initial

# Or reset and retry
python manage.py migrate subscriptions zero
python manage.py migrate subscriptions
```

### "DLL load failed" when installing psycopg2

```powershell
# Use binary version (no compilation needed)
pip uninstall psycopg2
pip install psycopg2-binary
```

---

## Quick Reference (Windows)

| Task | Command |
|------|---------|
| Start PostgreSQL | `Start-Service postgresql-x64-16` |
| Stop PostgreSQL | `Stop-Service postgresql-x64-16` |
| Restart PostgreSQL | `Restart-Service postgresql-x64-16` |
| Check status | `Get-Service postgresql*` |
| Connect to psql | `psql -U postgres` |
| List databases | `psql -U postgres -c "\l"` |
| Backup database | `pg_dump -Fc -U postgres weblift_prod > backup.dump` |
| Restore database | `pg_restore -U postgres -d weblift_prod backup.dump` |

---

## Next Steps

After PostgreSQL is configured:

1. **Run Django Migrations**
   ```powershell
   python manage.py migrate
   ```

2. **Collect Static Files**
   ```powershell
   python manage.py collectstatic
   ```

3. **Start Development Server**
   ```powershell
   python manage.py runserver
   ```

4. **Verify**
   Open http://localhost:8000 and test functionality

---

## Security Checklist for Windows

- [ ] PostgreSQL `postgres` password is strong (>20 chars)
- [ ] Database user `weblift_user` has minimal privileges (not superuser)
- [ ] pg_hba.conf only allows localhost connections (for local dev)
- [ ] Windows Firewall blocks port 5432 from external (if not needed)
- [ ] Backups are scheduled and tested
- [ ] .env file has restricted permissions (only owner can read)
- [ ] PostgreSQL service runs as limited user (not Administrator)
