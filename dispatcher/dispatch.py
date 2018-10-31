from time import sleep

from main import bot
from models import Student
from telebot.apihelper import ApiException

TIMEOUT = .4


def run_dispatch(message):
    received = 0
    users = Student.select()
    for user in users:
        try:
            bot.send_message(user.student_id, text=message)
            received += 1
        except ApiException:
            pass
        sleep(TIMEOUT)
    return f'{received}/{len(users)}'
