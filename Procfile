web: gunicorn Project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 --access-logfile - --error-logfile -

# Release phase: run migrations before starting the app
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput