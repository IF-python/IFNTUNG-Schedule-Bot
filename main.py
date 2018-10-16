import json
import utils
from models import Group
from time import sleep
from telebot import TeleBot
from difflib import get_close_matches
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.apihelper import ApiException

bot = TeleBot('677150470:AAGlNtWnU816rtoz2yttYjD4D2KQjNHVhJA')


@bot.message_handler(commands=['start'])
def greeting(message):
    bot.reply_to(message, text='Hello')


@bot.message_handler()
def test(message):
    text = message.text.upper()
    all_groups = utils.get_cached_groups()
    if text in all_groups:
        return bot.reply_to(message, text='OK')
    return suggest(message, text, all_groups)


def suggest(message, text, groups):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    matches = get_close_matches(text, groups, n=40, cutoff=0.5)
    if matches:
        markup.add(*matches)
        return bot.send_message(message.chat.id, text='Групу не знайдено. Ось схожі групи:',
                                reply_markup=markup)
    return bot.send_message(message.chat.id, text='Групу не знайдено.', reply_markup=ReplyKeyboardRemove())


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, timeout=10000)
            break
        except ApiException:
            bot.stop_polling()
            sleep(15)
