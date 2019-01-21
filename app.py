import os

import telebot
from flask import Flask, request

from main import bot, token

app = Flask(__name__)
secret = os.environ.get('SECRET')


@app.route('/' + token, methods=['POST'])
def receive_update():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@app.route("/" + secret)
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url='https://ifntungskedbot.herokuapp.com/' + token)
    return "RESET WEB HOOK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get('PORT', 5000))
