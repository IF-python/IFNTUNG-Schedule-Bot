web: gunicorn -w 4 app:app
worker: celery -B -A notifications worker -l debug
