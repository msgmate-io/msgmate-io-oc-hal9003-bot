## Hal 9003 ( `hal9003-msgmate-open-chat-bot` )

Open source, open-chat based Python AI bot.

## TL;DR

```bash
docker-compose up --build
```

### Running the bot locally

First setup your env in `.env`.
e.g.:

```
SERVER_HOST="localhost:8000"
SERVER_USE_SSL="false"
BOT_USERNAME="testBot1"
BOT_PASSWORD="Test123!"
WEBSOCKET_PORT="8000"
REDIS_URL="redis://host.docker.internal:6379/0"
DEBUG_CHAT_IDENTIFIER="<user-uuid>:<chat-uuid>"
AI_CONNECT_STRING=""
```

```bash
env $(cat .env | xargs) python3 -u bot.py
env $(cat .env | xargs) python3 -u api.py
```

### About

Build by [@tbscode](https://github.com/tbscode) to work with open-chat.
Checkout [open-chat](https://github.com/tbscode/django-vike-chat).