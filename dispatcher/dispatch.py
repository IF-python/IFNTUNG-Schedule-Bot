from time import sleep

from main import bot, ApiException
from models import Student


def run_dispatch(message):
    received = 0
    users = Student.select()
    for user in users:
        try:
            bot.send_message(user.student_id, text=message)
            received += 1
        except ApiException:
            pass
        sleep(0.4)
    return f'{received}/{len(users)}'
