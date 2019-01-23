web: gunicorn -w 4 app:app
worker: celery -A notifications worker -l debug -B
