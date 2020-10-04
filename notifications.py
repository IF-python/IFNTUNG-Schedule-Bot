import datetime
import os
from time import sleep

import peewee
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from telebot.apihelper import ApiException

from config import TIME_ZONE, redis_storage
from main import bot
from models import Student, database_proxy
from utils import get_schedule

prefix = '*Розклад на завтра.*\n'
app = Celery('notifications', broker='redis://bot_redis:6379/0')
app.conf.timezone = 'Europe/Kiev'
app.conf.beat_schedule = {
    'notify_every_week_day': {
        'task': 'notifications.main',
        'schedule': crontab(day_of_week='0-4')
    }
}


@worker_process_init.connect
def init_db_connection(*args, **kwargs):
    db = peewee.PostgresqlDatabase(
        'postgres', user='postgres', password=os.getenv("POSTGRES_PASSWORD"),
        host='bot_postgres', port=5432
    )
    database_proxy.initialize(db)


def notify(group, user_id, flag):
    try:
        bot.send_message(user_id, text=prefix + get_schedule('Завтра', group, bot, user_id, flag),
                         parse_mode='Markdown')
    except ApiException:
        pass


@app.task(ignore_result=True)
def main():
    current_time = datetime.datetime.now(TIME_ZONE).time().replace(second=0, microsecond=0)
    target_users = Student.at_time(current_time)
    for user in target_users:
        notify(user.group.group_code, user.student_id, user.extend)
        sleep(0.05)
    return current_time, target_users
