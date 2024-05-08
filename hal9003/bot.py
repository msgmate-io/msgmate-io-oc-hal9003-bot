import os
import base64
import json
import time
import subprocess
import time
import sys

import asyncio
from open_chat_api_client.api.user import user_self_retrieve
from open_chat_api_client.models import UserSelf
from bot import hal9003, prepare_client
from autobahn.asyncio.websocket import WebSocketClientFactory
from bot import config as bc
    
print("Full server URL:", bc.FULL_SERVER_URL)
print("Full websocket URL:", bc.FULL_WEBSOCKET_URL)

GLOBAL_REDIS_URL = bc.REDIS_URL

def login_bot():
    auth_client, csrftoken, sessionid = prepare_client.prepare_client(
        bot_username=bc.BOT_USERNAME,
        bot_password=bc.BOT_PASSWORD,
        server_url=bc.FULL_SERVER_URL
    )
    hal9003.GLOBAL_API_CLIENT = auth_client
    hal9003.GLOBAL_REDIS_URL = GLOBAL_REDIS_URL
    res2: UserSelf = user_self_retrieve.sync(client=auth_client)
    return {
        'user': res2,
        'csrftoken': csrftoken,
        'sessionid': sessionid
    }

def start_bot(
    csrftoken: str,
    sessionid: str
):
    factory = WebSocketClientFactory(bc.FULL_WEBSOCKET_URL)
    factory.protocol = hal9003.Hal9003
    factory.headers = {
        "X-CSRFToken": csrftoken,
        "Cookie": f"sessionid={sessionid}; csrftoken={csrftoken}"
    }
    
    def custom_exception_handler(loop, context):
        loop.default_exception_handler(context)

        exception = context.get('exception')
        if isinstance(exception, Exception):
            print(context)
            loop.stop()


    loop = asyncio.get_event_loop()
    loop.set_exception_handler(custom_exception_handler)
    coro = loop.create_connection(factory, bc.LOOP_HOST, ssl=bc.SERVER_USE_SSL, port=bc.WEBSOCKET_PORT)
    loop.run_until_complete(coro)
    loop.run_forever()
    if not bc.INFINITE_RETRY:
        loop.close()
        

if __name__ == '__main__':
    
    if bc.DJANGO_SERVER_ONLY:
        os.system(f"python3 server.py")
        exit(0)

    if bc.DEMONIZE_SELF:
        from bot import demon
        already_demon = demon.demonize_self_linux()
        if not already_demon:
            exit(0)
    
    # Start the Django server using subprocess and get the process ID
    if not bc.BOT_ONLY:
        server_process = subprocess.Popen(["python3", "server.py"], stdout=sys.stdout, stderr=subprocess.PIPE)
        server_pid = str(server_process.pid)
    
    try:
        if bc.INFINITE_RETRY:
            while True:
                try:
                    auth_bot = login_bot()
                    start_bot(auth_bot['csrftoken'], auth_bot['sessionid'])
                except Exception as e:
                    print("Error:", e)
                    print(f"Retrying in {bc.INFINITE_RETRY_INTERVAL} seconds")
                time.sleep(bc.INFINITE_RETRY_INTERVAL)
        else:
            auth_bot = login_bot()
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        server_process.terminate()
        server_process.kill()
        # also kill 'server_pid'
        os.kill(int(server_pid), 9)
        exit(0)