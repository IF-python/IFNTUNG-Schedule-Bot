import os
from difflib import get_close_matches

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

import utils
from models import Group, Student
from templates import chair_info, notify_template, time_menu_template
from config import default_time_set

token = os.environ.get('BOT_TOKEN')
bot = TeleBot(token)


@bot.message_handler(func=lambda m: utils.r.get(m.chat.id) == b'set_group')
@utils.throttle(time=1)
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
    utils.r.delete(user)
    return bot.edit_message_text(chat_id=user, message_id=call.message.message_id, text='Відмінено')


@bot.message_handler(commands=['set'])
@utils.throttle()
def set_group_command(message):
    return wait_for_group(message)


@bot.message_handler(commands=['get'])
@utils.throttle()
@utils.group_required(wait_for_group)
def get_my_group(message, *args):
    user = message.from_user.id
    desc = Student.get_group_desc(message.chat.id)
    return bot.send_message(user, text=utils.group_info.format(**desc))


def create_notify_keyboard(user):
    keyboard = InlineKeyboardMarkup()
    user_notify_status = Student.get_user_notify_status(user)
    turn = 'Увімкнути' if not user_notify_status else 'Вимкнути'
    notify_status_btn = InlineKeyboardButton(text=turn, callback_data='change_notify_status')
    set_time_btn = InlineKeyboardButton(text='Встановити час', callback_data='set_time')
    close_btn = InlineKeyboardButton(text='Закрити', callback_data='close')
    keyboard.add(notify_status_btn, set_time_btn)
    keyboard.add(close_btn)
    return keyboard


def create_time_buttons():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*[InlineKeyboardButton(text=time, callback_data=f'time_{time}')
                   for time in default_time_set])
    return keyboard


@bot.message_handler(func=lambda m: utils.r.get(m.chat.id) == b'set_time')
@utils.throttle(time=1)
def handle_notify_time(message):
    user = message.chat.id
    time = utils.validate_time(message.text)
    if not time:
        bot.send_message(chat_id=user, text='Хибний формат часу, спробуйте знову:', reply_markup=get_cancel_button())
    else:
        Student.set_notify_time(user, time)
        bot.delete_message(chat_id=user, message_id=utils.r.get(f'{user}::time_id'))
        bot.send_message(chat_id=user, text=f'Тепер Ви будете отримувати сповіщення о {time}.')


@bot.callback_query_handler(func=lambda call: call.data == 'set_time')
def set_notify_time_menu(call):
    user = call.from_user.id
    msg_id = bot.edit_message_text(message_id=call.message.message_id,
                                   chat_id=user, reply_markup=create_time_buttons(),
                                   text=time_menu_template)
    utils.r.set(user, 'set_time')
    utils.r.set(f'{user}::time_id', msg_id.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'change_notify_status')
def change_notify_status(call):
    user = call.from_user.id
    Student.trigger_notify(user)
    bot.edit_message_reply_markup(user, message_id=call.message.message_id, reply_markup=create_notify_keyboard(user))


@bot.message_handler(commands=['notify'])
@utils.throttle()
@utils.group_required(wait_for_group)
def notification_menu(message, *args):
    user = message.chat.id
    notify_time = Student.get_notify_time(user)
    bot.send_message(user, text=notify_template.format(notify_time),
                     reply_markup=create_notify_keyboard(user), parse_mode='Markdown')


def get_chair_status_message(user):
    current_state = Student.get_extend_flag(user)
    return chair_info.format(current_state)


def settings_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='Змінити', callback_data='change_chair'),
               InlineKeyboardButton(text='Закрити', callback_data='close'))
    return markup


@bot.message_handler(commands=['chair'])
@utils.throttle()
@utils.group_required(wait_for_group)
def get_change_chair_dialog(message, *args):
    user = message.from_user.id
    bot.send_message(user, text=get_chair_status_message(user),
                     reply_markup=settings_buttons(), parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'change_chair')
def reset_chair_status(call):
    user = call.from_user.id
    Student.reset_extended_flag(user)
    bot.edit_message_text(chat_id=user, message_id=call.message.message_id,
                          text=get_chair_status_message(user), parse_mode='Markdown',
                          reply_markup=settings_buttons())


@bot.callback_query_handler(func=lambda call: call.data == 'close')
def close_chair_dialog(call):
    user = call.from_user.id
    bot.edit_message_text(chat_id=user, message_id=call.message.message_id, text=':)')


@bot.message_handler(commands=['start'])
@utils.throttle()
@utils.group_required(wait_for_group)
def greeting(message, *args):
    return send_buttons(message)


@bot.message_handler(commands=['info'])
@utils.throttle()
def get_stats(message):
    user = message.from_user.id
    requests_count = utils.requests_limit_per_day - int(utils.get_requests_count(user))
    bot.send_message(user, parse_mode='Markdown', disable_web_page_preview=True,
                     text=utils.info_message.format(len(Student.select()), requests_count))


@bot.message_handler(func=lambda m: m.text in utils.days)
@utils.throttle()
@utils.limit_requests
@utils.in_thread
@utils.group_required(wait_for_group)
def send_schedule(message, user, group):
    extended_flag = Student.get_extend_flag(user)
    bot.send_message(user, text=utils.get_schedule(message.text, group, bot, user, extended_flag),
                     reply_to_message_id=message.message_id, parse_mode='Markdown')
    utils.track(str(user), 'Get schedule')


@bot.message_handler(commands=['date'])
@utils.throttle()
@utils.limit_requests
@utils.in_thread
@utils.group_required(wait_for_group)
def certain_date(message, user, group):
    splited = message.text.split()
    bot.send_chat_action(user, 'typing')
    extended_flag = Student.get_extend_flag(user)
    if len(splited) == 2:
        bot.send_message(user, text=utils.from_string(splited[1], group, extended_flag),
                         reply_to_message_id=message.message_id, parse_mode='Markdown')
    else:
        bot.reply_to(message, text='Хибний формат команди.')
    utils.track(str(user), 'Get schedule')


@bot.message_handler(regexp='Вказати конкретну дату')
@utils.throttle()
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
