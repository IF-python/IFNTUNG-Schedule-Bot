import os
import utils

from time import sleep
from telebot import TeleBot
from models import Group, Student
from difflib import get_close_matches
from telebot.apihelper import ApiException
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

bot = TeleBot(os.environ.get('BOT_TOKEN'))


@bot.message_handler(func=lambda m: utils.r.get(m.chat.id) == b'set_group')
def handle_group(message):
    user = message.from_user.id
    group = message.text.upper()
    all_groups = utils.get_cached_groups()
    if group.upper() in all_groups:
        utils.r.delete(user)
        Student.set_group(group_code=group, student_id=user)
        group_full = Group.get_group_full_name(group)
        bot.send_message(user, text=utils.set_group_message.format(group_full, group))
        return send_buttons(message)
    return suggest(message, group, all_groups)


def get_cancel_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='Відміна', callback_data='cancel'))
    return markup


def wait_for_group(message):
    user = message.from_user.id
    utils.r.set(user, 'set_group')
    return bot.send_message(user, text='Відправте шифр вашої групи:', reply_markup=get_cancel_button())


@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel(call):
    user = call.from_user.id
    if utils.r.get(user):
        utils.r.delete(user)
        bot.answer_callback_query(call.id, text='Відмінено')
    return bot.edit_message_text(chat_id=user, message_id=call.message.message_id, text='Відмінено')


@bot.message_handler(commands=['set'])
def set_group_command(message):
    return wait_for_group(message)


@bot.message_handler(commands=['get'])
def get_my_group(message):
    user = message.from_user.id
    desc = Student.get_group_desc(message.chat.id)
    if desc:
        return bot.send_message(user, text=utils.group_info.format(**desc))
    return wait_for_group(message)


@bot.message_handler(commands=['start'])
@utils.group_required(wait_for_group)
def greeting(message, _):
    return send_buttons(message)


@bot.message_handler(commands=['stats'])
def get_stats(message):
    bot.reply_to(message, text='Users: {}'.format(len(Student.select())))


@bot.message_handler(func=lambda m: m.text in utils.days)
@utils.group_required(wait_for_group)
def send_schedule(message, group):
    user = message.from_user.id
    bot.send_message(user, text=utils.get_schedule(message.text, group),
                     reply_to_message_id=message.message_id, parse_mode='Markdown')
    utils.track(str(user), 'Get schedule')


@bot.message_handler(commands=['date'])
@utils.group_required(wait_for_group)
def certain_date(message, group):
    user = message.from_user.id
    splited = message.text.split()
    if len(splited) == 2:
        bot.send_message(user, text=utils.from_string(splited[1], group),
                         reply_to_message_id=message.message_id, parse_mode='Markdown')
    else:
        bot.reply_to(message, text='Хибний формат команди.')
    utils.track(str(user), 'Get schedule')


@bot.message_handler(regexp='Вказати конкретну дату')
def send_tip(message):
    bot.reply_to(message, text=utils.tip_message)


def send_buttons(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*utils.days)
    markup.add('Вказати конкретну дату')
    bot.send_message(message.from_user.id, text='Меню', reply_markup=markup)


def suggest(message, group, groups):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    matches = get_close_matches(group, groups, n=25, cutoff=0.5)
    if matches:
        markup.add(*matches)
        return bot.send_message(message.chat.id,
                                text=utils.suggest_message,
                                reply_markup=markup)
    return bot.send_message(message.chat.id,
                            text=utils.group_not_found,
                            reply_markup=ReplyKeyboardRemove())


def main():
    bot.skip_pending = True
    while True:
        try:
            utils.logger.info('START POLLING')
            bot.polling(none_stop=True, timeout=utils.TIMEOUT)
            break
        except ApiException:
            utils.logger.error('RESTART POLLING')
            sleep(10)
            bot.stop_polling()


if __name__ == '__main__':
    main()
