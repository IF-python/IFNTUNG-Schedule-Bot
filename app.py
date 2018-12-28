import os

import telebot
from flask import Flask, request

from main import bot, token

server = Flask(__name__)


@server.route('/' + token, methods=['POST'])
def receive_update():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url='https://your_heroku_project.com/' + token)
    return "RESET WEB HOOK", 200


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
