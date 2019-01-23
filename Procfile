web: gunicorn -w 4 app:app
worker: celery -A notifications worker -l debug
worker: celery -A notifications beat -l debug
