import os
import base64
import json
print("Loading config")

ENV_FROM_B64_DICT = os.environ.get('ENV_FROM_B64_DICT', None)
print("ENV_FROM_B64_DICT:", ENV_FROM_B64_DICT)

if ENV_FROM_B64_DICT:
    os.environ.update(json.loads(base64.b64decode(ENV_FROM_B64_DICT).decode()))

DEBUG = os.environ.get('DEBUG', 'true').lower() in ('true', '1', 't')

USE_REDIS = os.environ.get('USE_REDIS', 'false').lower() in ('true', '1', 't')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')
SERVER_USE_SSL = os.environ.get("SERVER_USE_SSL", "true").lower() in ('true', '1', 't')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'testBot2')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', 'Test123!')
WEBSOCKET_PORT = os.environ.get('WEBSOCKET_PORT', 80 if SERVER_USE_SSL else 443)

DEBUG_CHAT_IDENTIFIER = os.environ.get('DEBUG_CHAT_IDENTIFIER', ':')
GLOBAL_DEBUG_CHAT_UUID, GLOBAL_DEBUG_RECIPIENT_UUID = DEBUG_CHAT_IDENTIFIER.split(':')

# [name, api_key, host, default_model]
GLOBAL_AI_BACKENDS = [backend.split("@") for backend in os.environ.get("AI_CONNECT_STRING", "@@").split(",")]

print("DEBUG_CHAT_IDENTIFIER:", DEBUG_CHAT_IDENTIFIER)

print("Connecting to", SERVER_HOST, "with SSL" if SERVER_USE_SSL else "without SSL")

HTTP_PROTOCOL = ('https' if SERVER_USE_SSL else 'http') + '://'
WEBSOCKET_PROTOCOL = ('wss' if SERVER_USE_SSL else 'ws') + '://'
FULL_SERVER_URL = HTTP_PROTOCOL + SERVER_HOST
FULL_WEBSOCKET_URL = WEBSOCKET_PROTOCOL + SERVER_HOST + '/api/core/ws'
# Check if `SERVER_HOST` contains a port number and split it
LOOP_HOST = SERVER_HOST
if ':' in SERVER_HOST:
    LOOP_HOST, _ = SERVER_HOST.split(':')
    
DEMONIZE_SELF = os.environ.get('DEMONIZE_SELF', 'false').lower() in ('true', '1', 't')
DEMON_VERSION = os.environ.get('DEMON_VERSION', 'v1')

INFINITE_RETRY = os.environ.get('INFINITE_RETRY', 'false').lower() in ('true', '1', 't')
INFINITE_RETRY_INTERVAL = int(os.environ.get('RETRY_INTERVAL', "5"))


INTERNAL_COMMUNICATION_PORT = int(os.environ.get('INTERNAL_COMMUNICATION_PORT', '8080'))
INTERNAL_COMMUNICATION_SECRET = os.environ.get('INTERNAL_COMMUNICATION_SECRET', 'test')
BOT_SERVER_GET_REQUEST_TOKEN = os.environ.get('BOT_SERVER_REQUEST_TOKEN', 'test')
BOT_SERVER_POST_REQUEST_TOKEN = os.environ.get('BOT_SERVER_POST_REQUEST_TOKEN', 'test')

DJANGO_SERVER_HOST = os.environ.get('DJANGO_SERVER_HOST', '0.0.0.0')
DJANGO_SERVER_PORT = int(os.environ.get('DJANGO_SERVER_PORT', '3445'))

DJANGO_SERVER_ONLY = os.environ.get('DJANGO_SERVER_ONLY', 'false').lower() in ('true', '1', 't')
BOT_ONLY = os.environ.get('BOT_ONLY', 'false').lower() in ('true', '1', 't')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
DEEPINFRA_API_KEY = os.environ.get('DEEPINFRA_API_KEY', '')
    
print("FULL_SERVER_URL:", FULL_SERVER_URL)