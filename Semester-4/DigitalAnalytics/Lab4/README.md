# Лаб. 4 — Telegram-бот на webhook'ах

Доработка бота из лаб. 3: переход с polling на webhook + усовершенствование
хранения пользовательских данных.

## Файлы
- `bot_polling.py` — исходная реализация на polling (для демонстрации недостатков).
- `storage.py` — улучшенное хранение: SQLite + PBKDF2-HMAC-SHA256 + блокировки.
- `bot_webhook.py` — Flask-приложение, принимающее обновления от Telegram API.
- `set_webhook.py` — утилита для регистрации webhook через `setWebhook`.
- `ml_predict.py` — адаптер модели ResNet-18 из `../Lab3/`.

## Деплой на pythonanywhere

1. Создать аккаунт на https://www.pythonanywhere.com, в разделе **Web** добавить
   новое Flask-приложение, указав путь к `bot_webhook.py` (или прописать
   `bot_webhook:app` в WSGI-файле).
2. В `Files` загрузить файлы лабораторной и веса `weights.pt` из лаб. 3.
3. Установить зависимости: `pip install --user -r requirements.txt`.
4. Прописать переменную окружения `BOT_TOKEN` (вкладка **Web → Environment variables**).
5. Перезапустить веб-приложение.
6. Зарегистрировать webhook:
   `BOT_TOKEN=... python set_webhook.py set https://<user>.pythonanywhere.com`.

## Команды бота
- `/register` — регистрация (запросит пароль следующим сообщением).
- `/login` — вход.
- `/predict` — отправить изображение для бинарной классификации (human/animal).
- `/logout` — выход.
