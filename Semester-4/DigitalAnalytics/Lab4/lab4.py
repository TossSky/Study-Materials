import logging
import os
from typing import Dict, Optional

import telebot
from telebot import TeleBot
from flask import Flask, Response, request

from predict import predict_image

TOKEN = os.environ.get("BOT_TOKEN", "0000000000:placeholder_token_replace_via_env")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://example.com")
PORT = 8080

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_storage: Dict[int, Dict[str, Optional[str | bool]]] = {}
model = None

bot: Optional[TeleBot] = None
flask_app = None


def get_bot() -> TeleBot:
    global bot
    if bot is None:
        bot = TeleBot(TOKEN)
        _register_handlers(bot)
    return bot


def _register_handlers(bot: TeleBot) -> None:
    @bot.message_handler(commands=['start', 'help'])
    def handle_start(message):
        help_text = (
            "*Доступные команды:*\n\n"
            "/register <пароль> - регистрация нового пользователя\n"
            "/login <пароль>    - вход в систему\n"
            "/logout            - завершение сессии\n"
            "/predict           - классифицировать изображение (человек/животное)\n\n"
            "*Пример использования:*\n"
            "1. /register mysecretpass\n"
            "2. /login mysecretpass\n"
            "3. Отправьте фото с подписью /predict"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

    @bot.message_handler(commands=['register'])
    def handle_register(message):
        try:
            user_id = message.from_user.id
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                bot.send_message(message.chat.id, "Использование: /register <пароль>")
                return
            password = parts[1].strip()
            user_storage[user_id] = {"password": password, "authenticated": False}
            bot.send_message(message.chat.id, "Регистрация прошла успешно. Используйте /login.")
        except Exception as e:
            logger.exception("register failed")
            bot.send_message(message.chat.id, f"Ошибка регистрации: {e}")

    @bot.message_handler(commands=['login'])
    def handle_login(message):
        try:
            user_id = message.from_user.id
            parts = (message.text or "").split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                bot.send_message(message.chat.id, "Использование: /login <пароль>")
                return
            password = parts[1].strip()
            user = user_storage.get(user_id)
            if user is None:
                bot.send_message(message.chat.id, "Сначала зарегистрируйтесь: /register <пароль>")
                return
            if user.get("password") != password:
                bot.send_message(message.chat.id, "Неверный пароль")
                return
            user["authenticated"] = True
            bot.send_message(message.chat.id, "Вход выполнен")
        except Exception as e:
            logger.exception("login failed")
            bot.send_message(message.chat.id, f"Ошибка входа: {e}")

    @bot.message_handler(commands=['logout'])
    def handle_logout(message):
        try:
            user_id = message.from_user.id
            user = user_storage.get(user_id)
            if user is None or not user.get("authenticated"):
                bot.send_message(message.chat.id, "Вы не авторизованы")
                return
            user["authenticated"] = False
            bot.send_message(message.chat.id, "Вы вышли из системы")
        except Exception as e:
            logger.exception("logout failed")
            bot.send_message(message.chat.id, f"Ошибка выхода: {e}")

    @bot.message_handler(commands=['predict'], content_types=['photo'])
    def handle_predict(message):
        try:
            user_id = message.from_user.id
            user = user_storage.get(user_id)
            if user is None or not user.get("authenticated"):
                bot.send_message(message.chat.id, "Вы не авторизованы, сначала используйте /login")
                return
            if not getattr(message, "photo", None):
                bot.send_message(message.chat.id, "Отправьте изображение с подписью /predict")
                return
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            image_bytes = bot.download_file(file_info.file_path)
            label = predict_image(image_bytes)
            bot.send_message(message.chat.id, label)
        except Exception as e:
            logger.exception("predict failed")
            bot.send_message(message.chat.id, f"Ошибка классификации: {e}")

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        try:
            user_id = message.from_user.id
            user = user_storage.get(user_id)
            if user is None or not user.get("authenticated"):
                bot.send_message(message.chat.id, "Вы не авторизованы, сначала используйте /login")
                return
            bot.send_message(message.chat.id, "Используйте команду /predict для классификации изображения")
        except Exception as e:
            logger.exception("photo failed")
            bot.send_message(message.chat.id, f"Ошибка обработки фото: {e}")

    @bot.message_handler(func=lambda m: True)
    def handle_unknown(message):
        bot.send_message(message.chat.id, "Неизвестная команда. /help — список команд.")


def get_flask_app() -> Flask:
    global flask_app
    if flask_app is None:
        flask_app = Flask(__name__)
        _setup_routes(flask_app)
    return flask_app


def _setup_routes(app: Flask) -> None:
    if app is None:
        return

    @app.route(f"/{TOKEN}", methods=['POST'])
    def telegram_webhook():
        if not bot:
            return Response("Bot not initialized", status=500)
        json_data = request.json
        if json_data:
            bot.process_new_updates([telebot.types.Update.de_json(json_data)])
        return Response("OK")

    @app.route("/health", methods=['GET'])
    def healthcheck():
        return Response("OK")


if __name__ == "__main__":
    get_bot()
    app = get_flask_app()
    if WEBHOOK_URL:
        get_bot().remove_webhook()
        get_bot().set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
