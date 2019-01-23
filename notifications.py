import datetime
import os
from time import sleep

from celery import Celery
from celery.schedules import crontab
from playhouse.db_url import connect

from config import TIME_ZONE
from main import bot
from models import Student, database_proxy
from utils import get_schedule

app = Celery('notifications', broker=os.environ.get('REDIS_URL'))
app.conf.beat_schedule = {
    'notify_every_week_day': {
        'task': 'notifications.main',
        'schedule': crontab()
    },
}


def notify(group, user_id, flag):
    bot.send_message(user_id, text=get_schedule('Сьогодні', group, bot, user_id, flag))


@app.task
def main():
    db = connect(os.environ.get('DATABASE_URL'))
    database_proxy.initialize(db)
    current_time = datetime.datetime.now(TIME_ZONE).time().replace(second=0, microsecond=0)
    target_users = Student.at_time(current_time)
    for user in target_users:
        notify(user.group.group_code, user.student_id, user.extend)
        sleep(0.05)
    return current_time, target_users
