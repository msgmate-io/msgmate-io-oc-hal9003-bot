import os
import sys
from dataclasses import dataclass
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path
from django.utils.crypto import get_random_string
from bot.prepare_client import prepare_client
from bot import config as bc

settings.configure(
    DEBUG=bc.DEBUG,
    ALLOWED_HOSTS=["*"],
    ROOT_URLCONF=__name__,
    SECRET_KEY=get_random_string(
        50
    ),
    MIDDLEWARE=["django.middleware.common.CommonMiddleware"],
    REST_FRAMEWORK={
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer"
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny"
    ], 
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ]},
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        "django.contrib.sessions",
        "django.contrib.messages",
        "rest_framework",
    ],
)

auth_client, csrftoken, sessionid = prepare_client(
    bot_username=bc.BOT_USERNAME,
    bot_password=bc.BOT_PASSWORD,
    server_url=bc.FULL_SERVER_URL
)

from server import api

api.auth_client = auth_client

urlpatterns = [
    path("", api.index),
]

if bc.DEBUG:
    urlpatterns += [
        path("get_debug_relay", api.get_debug_relay),
        path("c/<str:chat_uuid>/<str:recipient_uuid>/", api.message_send),
    ]

app = get_wsgi_application()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    
    if len(sys.argv) == 1:
        # also set 0.0.0.0
        sys.argv += ["runserver", bc.DJANGO_SERVER_HOST + ":" + str(bc.DJANGO_SERVER_PORT)]

    execute_from_command_line(sys.argv)