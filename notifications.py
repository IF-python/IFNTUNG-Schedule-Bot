import datetime
import os
from time import sleep

from celery import Celery, Task
from celery.schedules import crontab

from config import TIME_ZONE
from main import bot
from models import Student, db
from utils import get_schedule

app = Celery('notifications', broker=os.environ.get('REDIS_URL'))

app.conf.beat_schedule = {
    'notify_every_week_day': {
        'task': 'notifications.main',
        'schedule': crontab()
    },
}


class DatabaseTask(Task):
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = db.connect()
        return self._db


def notify(group, user_id, flag):
    bot.send_message(user_id, text=get_schedule('Сьогодні', group, bot, user_id, flag))


@app.task(base=DatabaseTask)
def main():
    current_time = TIME_ZONE.localize(datetime.datetime.now()).time().replace(second=0, microsecond=0)
    target_users = Student.at_time(current_time)
    for user in target_users:
        notify(user.group.group_code, user.student_id, user.extend)
        sleep(0.05)
