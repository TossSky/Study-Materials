from __future__ import annotations

import os
import tempfile

import requests
from flask import Flask, abort, request

import storage
import ml_predict

BOT_TOKEN = os.environ.get("BOT_TOKEN", "<PUT_TOKEN_HERE>")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)
storage.init_db()

HELP = (
    "Доступные команды:\n"
    "/register — регистрация\n"
    "/login — вход\n"
    "/predict — классификация изображения\n"
    "/logout — выход"
)


def send_message(chat_id: int, text: str) -> None:
    requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)


def download_photo(file_id: str) -> str:
    info = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=10).json()
    file_path = info["result"]["file_path"]
    data = requests.get(f"{FILE_API}/{file_path}", timeout=30).content
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(data)
    tmp.close()
    return tmp.name


def handle_command(chat_id: int, cmd: str) -> None:
    if cmd in ("/start", "/help"):
        send_message(chat_id, HELP)
        return

    if cmd == "/register":
        if storage.exists(chat_id):
            send_message(chat_id, "Вы уже зарегистрированы.")
            return
        storage.set_pending(chat_id, "await_register_password")
        send_message(chat_id, "Введите пароль для регистрации:")
        return

    if cmd == "/login":
        if not storage.exists(chat_id):
            send_message(chat_id, "Сначала пройдите регистрацию: /register.")
            return
        storage.set_pending(chat_id, "await_login_password")
        send_message(chat_id, "Введите пароль:")
        return

    if cmd == "/logout":
        if storage.is_logged_in(chat_id):
            storage.set_logged_in(chat_id, False)
            send_message(chat_id, "Вы вышли из системы.")
        else:
            send_message(chat_id, "Вы и так не авторизованы.")
        return

    if cmd == "/predict":
        if not storage.is_logged_in(chat_id):
            send_message(chat_id, "Требуется аутентификация: /login.")
            return
        storage.set_pending(chat_id, "await_image")
        send_message(chat_id, "Отправьте изображение.")
        return

    send_message(chat_id, "Неизвестная команда. /help — список.")


def handle_text(chat_id: int, text: str) -> None:
    pending = storage.get_pending(chat_id)
    if pending == "await_register_password":
        if storage.register(chat_id, text):
            send_message(chat_id, "Регистрация прошла успешно. Войдите через /login.")
        else:
            send_message(chat_id, "Пользователь уже существует.")
        storage.clear_pending(chat_id)
        return

    if pending == "await_login_password":
        if storage.verify(chat_id, text):
            storage.set_logged_in(chat_id, True)
            send_message(chat_id, "Аутентификация успешна.")
        else:
            send_message(chat_id, "Неверный пароль.")
        storage.clear_pending(chat_id)
        return

    send_message(chat_id, "Неизвестная команда. /help — список.")


def handle_photo(chat_id: int, file_id: str) -> None:
    if storage.get_pending(chat_id) != "await_image":
        send_message(chat_id, "Сначала отправьте команду /predict.")
        return
    if not storage.is_logged_in(chat_id):
        send_message(chat_id, "Требуется аутентификация: /login.")
        return

    path = download_photo(file_id)
    try:
        label, prob = ml_predict.predict_image(path)
        send_message(chat_id, f"На изображении: {label} (p={prob:.3f}).")
    finally:
        storage.clear_pending(chat_id)
        try:
            os.unlink(path)
        except OSError:
            pass


@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True, silent=True)
    if not update:
        abort(400)

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok"
    chat_id = msg["chat"]["id"]

    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        handle_photo(chat_id, file_id)
    elif "text" in msg:
        text = msg["text"]
        if text.startswith("/"):
            handle_command(chat_id, text.split()[0])
        else:
            handle_text(chat_id, text)
    return "ok"


@app.get("/")
def index():
    return "Lab4 webhook bot is running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
