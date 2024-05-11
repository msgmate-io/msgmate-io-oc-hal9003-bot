## Hal 9003 ( `hal9003-msgmate-open-chat-bot` )

Open source, open-chat based Python AI bot.

## TL;DR

Starts all services with all features and auto-reload.

```bash
docker-compose up --build
```

### Using the bot with OpenAI-API

First setup your env in `.env`, add the following to your default setup:
e.g. use the following setup with your own `OPENAI_API_KEY`, to use the bot in development:

```bash
MODEL_BACKEND="openai"
DEFAULT_MODEL="gpt-3.5-turbo"
OPENAI_API_KEY="sk-***"
```

### Or use the bot using deepinfa

```bash
MODEL_BACKEND="deepinfra"
DEFAULT_MODEL="meta-llama/Meta-Llama-3-70B-Instruct"
DEEPINFRA_API_KEY="****"
```

### Running the bot outside of Docker

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r ./hal9003/requirements.txt
env $(cat .env | xargs) python3 -u hal9003/bot.py # start the bot
env $(cat .env | xargs) python3 -u hal9003/server.py # start the companion server
```

### Running Agent / Tests / Evaluations

```bash
env $(cat .env | xargs) python3 -u hal9003/agent.py
```

### About

Build by [@tbscode](https://github.com/tbscode) to work with open-chat.
Checkout [open-chat](https://github.com/tbscode/django-vike-chat).