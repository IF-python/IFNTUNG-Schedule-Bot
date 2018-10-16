import utils
from time import sleep
from telebot import TeleBot
from models import Group, Student
from difflib import get_close_matches
from telebot.apihelper import ApiException
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

bot = TeleBot('677150470:AAGlNtWnU816rtoz2yttYjD4D2KQjNHVhJA')


@bot.message_handler(func=lambda m: utils.r.get(m.chat.id) == b'set_group')
def handle_group(message):
    user = message.from_user.id
    group = message.text.upper()
    all_groups = utils.get_cached_groups()
    if group in all_groups:
        Student.set_group(group_code=group, student_id=user)
        group_full = Group.get_group_full_name(group)
        utils.r.delete(user)
        bot.send_message(user, text=utils.set_group_message.format(group_full, group))
        return send_buttons(message)
    return suggest(message, group, all_groups)


def wait_for_group(message):
    user = message.from_user.id
    utils.r.set(user, 'set_group')
    return bot.send_message(user, text='Відправте шифр вашої групи:')


@bot.message_handler(commands=['start'])
@utils.group_required(wait_for_group)
def greeting(message, _):
    return send_buttons(message)


def send_buttons(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('lol', 'kek')
    bot.send_message(message.from_user.id, text='Меню', reply_markup=markup)


def suggest(message, group, groups):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    matches = get_close_matches(group, groups, n=25, cutoff=0.5)
    if matches:
        markup.add(*matches)
        return bot.send_message(message.chat.id,
                                text=utils.group_not_found_message,
                                reply_markup=markup)
    return bot.send_message(message.chat.id,
                            text=utils.group_not_found_message[:17],
                            reply_markup=ReplyKeyboardRemove())


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, timeout=10000)
            break
        except ApiException:
            bot.stop_polling()
            sleep(15)
