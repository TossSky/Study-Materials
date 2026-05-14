import os

import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN", "<PUT_TOKEN_HERE>")
bot = telebot.TeleBot(BOT_TOKEN)

users: dict[int, dict] = {}
pending_action: dict[int, str] = {}


@bot.message_handler(commands=["start", "help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "Доступные команды:\n"
        "/register — регистрация\n"
        "/login — вход\n"
        "/predict — классификация изображения\n"
        "/logout — выход",
    )


@bot.message_handler(commands=["register"])
def cmd_register(message):
    chat_id = message.chat.id
    if chat_id in users:
        bot.send_message(chat_id, "Пользователь уже зарегистрирован.")
        return
    pending_action[chat_id] = "await_register_password"
    bot.send_message(chat_id, "Введите пароль для регистрации:")


@bot.message_handler(commands=["login"])
def cmd_login(message):
    chat_id = message.chat.id
    if chat_id not in users:
        bot.send_message(chat_id, "Сначала пройдите регистрацию: /register.")
        return
    pending_action[chat_id] = "await_login_password"
    bot.send_message(chat_id, "Введите пароль:")


@bot.message_handler(commands=["logout"])
def cmd_logout(message):
    chat_id = message.chat.id
    if chat_id in users and users[chat_id]["logged_in"]:
        users[chat_id]["logged_in"] = False
        bot.send_message(chat_id, "Вы вышли из системы.")
    else:
        bot.send_message(chat_id, "Сначала войдите: /login.")


@bot.message_handler(commands=["predict"])
def cmd_predict(message):
    chat_id = message.chat.id
    if chat_id not in users or not users[chat_id]["logged_in"]:
        bot.send_message(chat_id, "Требуется аутентификация: /login.")
        return
    pending_action[chat_id] = "await_image"
    bot.send_message(chat_id, "Отправьте изображение.")


@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    action = pending_action.get(chat_id)
    if action == "await_register_password":
        users[chat_id] = {"password": message.text, "logged_in": False}
        pending_action.pop(chat_id, None)
        bot.send_message(chat_id, "Регистрация прошла успешно.")
    elif action == "await_login_password":
        if users[chat_id]["password"] == message.text:
            users[chat_id]["logged_in"] = True
            pending_action.pop(chat_id, None)
            bot.send_message(chat_id, "Аутентификация успешна.")
        else:
            bot.send_message(chat_id, "Неверный пароль.")
    else:
        bot.send_message(chat_id, "Неизвестная команда. /help — список команд.")


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    if pending_action.get(chat_id) != "await_image":
        bot.send_message(chat_id, "Сначала отправьте команду /predict.")
        return
    pending_action.pop(chat_id, None)
    bot.send_message(chat_id, "Результат классификации: <stub>")


if __name__ == "__main__":
    bot.infinity_polling()
