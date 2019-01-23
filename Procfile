web: gunicorn -w 4 app:app
worker: celery worker -A notifications -l debug
worker: celery -A notifications beat -l debug
