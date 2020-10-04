from time import sleep

from telebot.apihelper import ApiException

from main import bot
from models import Student

TIMEOUT = 0.4


def run_dispatch(message):
    received = 0
    users = Student.select()
    for user in users:
        try:
            bot.send_message(user.student_id, text=message)
            received += 1
            print(received)
        except ApiException:
            pass
        sleep(TIMEOUT)
    return f"{received}/{len(users)}"
