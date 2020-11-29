import functools
import os
import time
from difflib import get_close_matches

from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

import utils
from config import DEFAULT_TIME_SET
from models import Group, Student
from templates import chair_info, notify_template, time_menu_template

token = os.environ.get("BOT_TOKEN")
bot = TeleBot(token)
bot.skip_pending = True


@bot.message_handler(func=lambda m: utils.redis_storage.get(m.chat.id) == b"set_group")
@utils.throttle(time=1)
def handle_group(message):
    user = message.from_user.id
    group = message.text.upper()
    if utils.get_or_create_group(group):
        utils.redis_storage.delete(user)
        Student.set_group(group_code=group, student_id=user)
        group_full = Group.get_group_full_name(group)
        bot.send_message(user, text=utils.set_group_message.format(group_full, group))
        return send_buttons(message)
    return suggest(message, group, utils.get_cached_groups())


@bot.message_handler(
    commands=["dispatch"], func=lambda m: m.from_user.id == utils.ADMIN_ID
)
@utils.in_thread
def handle_dispatch(message):
    data = message.text.split(maxsplit=1)
    if len(data) != 2:
        return bot.send_message(message.chat.id, text="Incorrect input.")
    return run_dispatch(message, data[1])


def run_dispatch(message, content):
    receivers = 0
    dispatch_format = "<b>Run dispatch</b>\n<pre>{}/{}</pre>"
    users = Student.select()
    response = bot.send_message(
        message.chat.id,
        text=dispatch_format.format(receivers, len(users)),
        parse_mode="html",
    )
    progress = functools.partial(
        bot.edit_message_text,
        chat_id=response.chat.id,
        message_id=response.message_id,
        parse_mode="html",
    )
    dispatch = functools.partial(bot.send_message, text=content, parse_mode="html")

    for user in users:
        try:
            dispatch(user.student_id)
            receivers += 1
            if not receivers % 100:
                progress(text=dispatch_format.format(receivers, len(users)))
        except ApiException as e:
            print(e)
        time.sleep(0.4)
    progress(text=dispatch_format.format(receivers, len(users)) + "\n<b>Successful</b>")


def get_cancel_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Відміна", callback_data="cancel"))
    return markup


def wait_for_group(message):
    user = message.from_user.id
    utils.redis_storage.set(user, "set_group")
    return bot.send_message(
        user, text="Відправте шифр вашої групи:", reply_markup=get_cancel_button()
    )


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel(call):
    user = call.from_user.id
    utils.redis_storage.delete(user)
    return bot.edit_message_text(
        chat_id=user, message_id=call.message.message_id, text="Відмінено"
    )


@bot.message_handler(commands=["set"])
@utils.throttle()
def set_group_command(message):
    return wait_for_group(message)


@bot.message_handler(commands=["get"])
@utils.throttle()
@utils.group_required(wait_for_group)
def get_my_group(message, *args):
    user = message.from_user.id
    desc = Student.get_group_desc(message.chat.id)
    return bot.send_message(user, text=utils.group_info.format(**desc))


def create_notify_keyboard(user):
    keyboard = InlineKeyboardMarkup()
    user_notify_status = Student.get_user_notify_status(user)
    turn = "Увімкнути" if not user_notify_status else "Вимкнути"
    notify_status_btn = InlineKeyboardButton(
        text=turn, callback_data="change_notify_status"
    )
    set_time_btn = InlineKeyboardButton(text="Встановити час", callback_data="set_time")
    close_btn = InlineKeyboardButton(text="Закрити", callback_data="close")
    keyboard.add(notify_status_btn, set_time_btn)
    keyboard.add(close_btn)
    return keyboard


def create_time_buttons():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        *[
            InlineKeyboardButton(text=_time, callback_data=f"time_{_time}")
            for _time in DEFAULT_TIME_SET
        ]
    )
    keyboard.add(
        InlineKeyboardButton(text="Назад", callback_data="back"),
        InlineKeyboardButton(text="Відміна", callback_data="cancel"),
    )
    return keyboard


@bot.callback_query_handler(func=lambda call: call.data == "back")
def back_to_notify(call):
    utils.redis_storage.delete(call.from_user.id)
    return make_notification_menu(
        message=call.message,
        action=bot.edit_message_text,
        message_id=call.message.message_id,
    )


@bot.message_handler(commands=["notify"])
@utils.throttle()
@utils.group_required(wait_for_group)
def notification_menu(message, *args):
    return make_notification_menu(message)


def make_notification_menu(message, action=bot.send_message, **kwargs):
    user = message.chat.id
    notify_time = Student.get_notify_time(user)
    action(
        chat_id=user,
        text=notify_template.format(notify_time or "Не вказано"),
        reply_markup=create_notify_keyboard(user),
        parse_mode="html",
        **kwargs,
    )


@bot.message_handler(func=lambda m: utils.redis_storage.get(m.chat.id) == b"set_time")
@utils.throttle(time=1)
def handle_notify_time(message):
    user = message.chat.id
    time = utils.validate_time(message.text)
    if not time:
        bot.send_message(
            chat_id=user,
            text="Хибний формат часу, спробуйте знову:",
            reply_markup=get_cancel_button(),
        )
    else:
        Student.set_notify_time(user, time)
        bot.delete_message(
            chat_id=user, message_id=utils.redis_storage.get(f"{user}::time_id")
        )
        bot.send_message(
            chat_id=user,
            text=f"Тепер Ви будете отримувати сповіщення о <b>{time.time()}</b>.",
            parse_mode="html",
        )
        utils.redis_storage.delete(user)


@bot.callback_query_handler(func=lambda call: call.data.startswith("time"))
def handle_default_time(call):
    time = call.data.split("_")[1]
    user = call.from_user.id
    Student.set_notify_time(user, time)
    bot.edit_message_text(
        chat_id=user,
        text=f"Тепер Ви будете отримувати сповіщення о <b>{time}:00</b>.",
        message_id=call.message.message_id,
        parse_mode="html",
    )
    utils.redis_storage.delete(user)


@bot.callback_query_handler(func=lambda call: call.data == "set_time")
def set_notify_time_menu(call):
    user = call.from_user.id
    msg_id = bot.edit_message_text(
        message_id=call.message.message_id,
        chat_id=user,
        reply_markup=create_time_buttons(),
        text=time_menu_template,
    )
    utils.redis_storage.set(user, "set_time")
    utils.redis_storage.set(f"{user}::time_id", msg_id.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "change_notify_status")
def change_notify_status(call):
    user = call.from_user.id
    Student.trigger_notify(user)
    bot.edit_message_reply_markup(
        user,
        message_id=call.message.message_id,
        reply_markup=create_notify_keyboard(user),
    )


def get_chair_status_message(user):
    current_state = Student.get_extend_flag(user)
    return chair_info.format(current_state)


def settings_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="Змінити", callback_data="change_chair"),
        InlineKeyboardButton(text="Закрити", callback_data="close"),
    )
    return markup


@bot.message_handler(commands=["chair"])
@utils.throttle()
@utils.group_required(wait_for_group)
def get_change_chair_dialog(message, *args):
    user = message.from_user.id
    bot.send_message(
        user,
        text=get_chair_status_message(user),
        reply_markup=settings_buttons(),
        parse_mode="html",
    )


@bot.callback_query_handler(func=lambda call: call.data == "change_chair")
def reset_chair_status(call):
    user = call.from_user.id
    Student.reset_extended_flag(user)
    bot.edit_message_text(
        chat_id=user,
        message_id=call.message.message_id,
        text=get_chair_status_message(user),
        parse_mode="html",
        reply_markup=settings_buttons(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "close")
def close_chair_dialog(call):
    user = call.from_user.id
    bot.edit_message_text(chat_id=user, message_id=call.message.message_id, text=":)")


@bot.message_handler(commands=["start"])
@utils.throttle()
@utils.group_required(wait_for_group)
def greeting(message, *args):
    return send_buttons(message)


@bot.message_handler(commands=["suggest"])
def suggest_future(message):
    return NotImplementedError


def reached_requests_limit_markup(message):
    bot.send_message(
        chat_id=message.chat.id, text="Ви вичерпали ліміт запитів на сьогодні."
    )


@bot.message_handler(commands=["info"])
@utils.throttle()
def get_stats(message):
    user = message.from_user.id
    requests_count = utils.REQUESTS_LIMIT_PER_DAY - int(utils.get_requests_count(user))
    bot.send_message(
        user,
        parse_mode="html",
        disable_web_page_preview=True,
        text=utils.info_message.format(len(Student.select()), requests_count),
    )


@bot.message_handler(func=lambda m: m.text in utils.DAYS)
@utils.throttle()
@utils.limit_requests(reached_requests_limit_markup)
@utils.in_thread
@utils.group_required(wait_for_group)
def send_schedule(message, user, group):
    extended_flag = Student.get_extend_flag(user)
    bot.send_message(
        user,
        text=utils.get_schedule(message.text, group, bot, user, extended_flag),
        reply_to_message_id=message.message_id,
        parse_mode="html",
        disable_web_page_preview=True,
    )
    utils.track(user, "Get schedule")


def reached_limit_alert(callback):
    bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text="Ви вичерпали ліміт запитів на сьогодні.",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("weekday"))
@utils.limit_requests(reached_limit_alert)
@utils.in_thread
@utils.group_required(wait_for_group)
def handle_weekday(call, user, group):
    day = call.data.split("_")[1]
    extended_flag = Student.get_extend_flag(user)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back_weekdays"))
    bot.edit_message_text(
        chat_id=user,
        message_id=call.message.message_id,
        text=utils.week_day_schedule(
            utils.get_correct_day(int(day)), group, extended_flag
        ),
        parse_mode="html",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    utils.track(user, "Weekday schedule")


@bot.callback_query_handler(func=lambda call: call.data == "back_weekdays")
def back_to_weekdays(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Дні тижня:",
        reply_markup=build_weekdays_buttons(),
    )


@bot.message_handler(commands=["date"])
@utils.throttle()
@utils.limit_requests(reached_requests_limit_markup)
@utils.in_thread
@utils.group_required(wait_for_group)
def certain_date(message, user, group):
    splited = message.text.split()
    bot.send_chat_action(user, "typing")
    if len(splited) == 2:
        extended_flag = Student.get_extend_flag(user)
        bot.send_message(
            user,
            text=utils.from_string(splited[1], group, extended_flag),
            reply_to_message_id=message.message_id,
            parse_mode="html",
            disable_web_page_preview=True,
        )
    else:
        bot.reply_to(message, text="Хибний формат команди.")
    utils.track(user, "Get schedule")


@bot.message_handler(regexp="Вказати конкретну дату")
@utils.throttle()
def send_tip(message):
    bot.reply_to(message, text=utils.tip_message)


@bot.callback_query_handler(func=lambda call: call.data == "how_it_works")
def how_it_works(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back_weekdays"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=utils.weekdays_info,
        reply_markup=keyboard,
    )


def build_weekdays_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"weekday_{call}")
        for call, name in enumerate(utils.DAY_NAMES)
    ]
    buttons.append(InlineKeyboardButton(text="Закрити", callback_data="close"))
    buttons.append(
        InlineKeyboardButton(text="Як це працює?", callback_data="how_it_works")
    )
    keyboard.add(*buttons)
    return keyboard


@bot.message_handler(regexp="Дні тижня")
@utils.throttle()
def weekdays(message):
    bot.send_message(
        message.chat.id, text="Дні тижня:", reply_markup=build_weekdays_buttons()
    )


def send_buttons(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*utils.DAYS)
    markup.add("Вказати конкретну дату", "Дні тижня")
    bot.send_message(message.from_user.id, text="Меню", reply_markup=markup)


def suggest(message, group, groups):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    matches = get_close_matches(group, groups, n=25, cutoff=0.5)
    if matches:
        markup.add(*matches)
        return bot.send_message(
            message.chat.id, text=utils.suggest_message, reply_markup=markup
        )
    return bot.send_message(
        message.chat.id, text=utils.group_not_found, reply_markup=ReplyKeyboardRemove()
    )
