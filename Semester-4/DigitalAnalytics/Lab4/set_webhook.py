import os
import sys

import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "<PUT_TOKEN_HERE>")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "info"
    if action == "set":
        if len(sys.argv) < 3:
            sys.exit("Usage: set_webhook.py set <BASE_URL>")
        base = sys.argv[2].rstrip("/")
        url = f"{base}/{BOT_TOKEN}"
        r = requests.post(f"{API}/setWebhook", json={"url": url}, timeout=10)
    elif action == "delete":
        r = requests.post(f"{API}/deleteWebhook", timeout=10)
    else:
        r = requests.get(f"{API}/getWebhookInfo", timeout=10)
    print(r.json())


if __name__ == "__main__":
    main()
