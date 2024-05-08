from autobahn.asyncio.websocket import WebSocketClientProtocol
from aiohttp.web_runner import GracefulExit
import traceback
from aiohttp import web
from open_chat_api_client.models import Message, ChatResult
from openai import AsyncOpenAI
import dataclasses
from dataclasses import dataclass
import asyncio
import json
import uuid
from bot.manager import Manager, MessageContext
from bot.db import DB
from bot.cmd import CommandProcessor
from bot import config as bc
from bot.fmt import Formatter
from datetime import datetime

GLOBAL_REDIS_URL = bc.REDIS_URL
GLOBAL_API_CLIENT = None
COMMAND_PREFIXES = ['/', '!']

from multiprocessing import Process
        
class Hal9003(WebSocketClientProtocol):
    
    fmt = Formatter()
    cmd: CommandProcessor = None
    db: DB = None
    mng: Manager = None
    ai_client: AsyncOpenAI = None
    ai_config = None

    def __init__(self):
        super().__init__()
        self.db = DB(self, redis_url=GLOBAL_REDIS_URL, client=GLOBAL_API_CLIENT)

        self.mng = Manager(self, db=self.db)
        self.cmd = CommandProcessor(self)
        ai_backend = bc.GLOBAL_AI_BACKENDS[0][2]
        ai_api_key = bc.GLOBAL_AI_BACKENDS[0][1]
        self.ai_config = bc.GLOBAL_AI_BACKENDS[0]
        self.ai_client = AsyncOpenAI(api_key=ai_api_key, base_url=ai_backend if (ai_backend and ai_backend != '') else None)
        self.queue = asyncio.Queue()

    async def processCommandMessage(self, context: MessageContext):
        text = context.message.text
        assert text.startswith(tuple(COMMAND_PREFIXES))
        command = text.split()[0][1:]
        args = text.split()[1:]
        await self.cmd.run_command(command, args, context)
        
    async def processMessage(self, context: MessageContext):

        db_chat = await self.db.getChat(context.chat.uuid)
        if db_chat is None:
            await self.db.setChat(context.chat.uuid, context.chat)
            # check if the chat is loaded in 'db'
            db_chat = await self.db.getChat(context.chat.uuid)
            pretty_chat_json = await self.fmt.wrap_code(json.dumps(db_chat.to_dict(), indent=4))
            await self.mng.debugSend(f"Chat not found in db, created new chat\n - {context.chat.uuid}\n{pretty_chat_json}", context, verbose=2)
        else:
            pretty_chat_json = await self.fmt.wrap_code(json.dumps(db_chat.to_dict(), indent=4))
            await self.mng.debugSend(f"Chat found in db\n - {context.chat.uuid}\n{pretty_chat_json}", context, verbose=3)
        await self.aiChatResponse(context)
        
    async def aiChatResponse(self, context: MessageContext):
        # 0 - get the chat config
        _, config = await self.db.getOrCreateChatSettings(context.chat.uuid, mc=context)

        # 1 - get the chat messages
        message_history = await self.db.getOrFetchChatMessages(context.chat.uuid, incoming_message=context.message, min_context=config.context)
        pretty_message_history_json = await self.fmt.wrap_code(json.dumps([msg.to_dict() for msg in message_history], indent=4))
        await self.mng.debugSend(f"## Chat history\n - in chat `{context.chat.uuid}`\n - by sender `{context.senderId}`\n> {context.message.text}\n{pretty_message_history_json}", context, verbose=2)
        bot_user = await self.db.getOrFetchBotUser()
        user_messages = await self.fmt.openai_user_messages(message_history, bot_uuid=bot_user.uuid, context=config.context)
        messages = [
            {
                "role": "system",
                "content": config.systemPrompt
            },
            *user_messages
        ]
        
        pretty_messages_json = await self.fmt.wrap_code(json.dumps(messages, indent=4))
        await self.mng.debugSend(f"## AI Response triggered\n> {context.message.text}\n - in chat `{context.chat.uuid}`\n - by sender `{context.senderId}`\n{pretty_messages_json}", context, verbose=2)

        response = await self.ai_client.chat.completions.create(
            model=config.model,
            stream=True,
            messages=messages        
        )
        
        full_response = ""
        
        async for chunk in response:
            # await self.mng.debugSend(f"## AI Response chunk\n - in chat `{context.chat.uuid}`\n - by sender `{context.senderId}`\n> {chunk}", context)
            delta = chunk.choices[0].delta.content
            finished = chunk.choices[0].finish_reason
            if finished:
                await self.mng.sendChatMessage(context, full_response)
                # generate a random tmp uuid
                tmp_uuid = str(uuid.uuid4())
                usage = getattr(chunk, 'usage', None)
                if usage:
                    await self.mng.debugSend(f"## AI Response steam completed\n - in chat `{context.chat.uuid}`\n - by sender `{context.senderId}`\n> {full_response}\n - usage: {usage}", context)
                await self.db.addChatMessage(context.chat.uuid, Message(
                    uuid=f"tmp-{tmp_uuid}",
                    sender=bot_user.uuid,
                    created=datetime.now(),
                    text=full_response,
                    read=False
                ))
                await self.mng.debugSend(f"## AI Response steam completed\n - in chat `{context.chat.uuid}`\n - by sender `{context.senderId}`\n> {full_response}", context)
            elif delta:
                full_response += delta
                await self.mng.sendPartialMessage(context, full_response)
    
    async def _newMessage(self, context: MessageContext):
        pretty_message_json = await self.fmt.wrap_code(json.dumps(context.message.to_dict(), indent=4))
        debug_message = f"## Message\n> {context.message.text}\n- from `{context.senderId}`\n- in chat `{context.chat.uuid}`\n" + pretty_message_json
        await self.mng.debugSend(debug_message, context)
        # check if the message is a 'command'
        if context.message.text.startswith(tuple(COMMAND_PREFIXES)):
            # command detected
            await self.processCommandMessage(context)
        else:
            # default message processing
            await self.processMessage(context)

    async def onProcessCustomMessage(self, action, payload):
        print("Processing custom message: '{0}' with payload: {1}".format(action, payload))
        
        if action == 'newMessage':
            message = payload.get('message')
            senderId = payload.get('senderId')
            chat = payload.get('chat')
            print("New message from", senderId, "in chat", chat, ":", message)
            if 'settings' in chat and chat['settings'] is None:
                del chat['settings'] # remove None settings
            mc = MessageContext(Message.from_dict(message), senderId, ChatResult.from_dict(chat))
            try:
                await asyncio.create_task(self._newMessage(mc))
            except Exception as ex:
                trace = await self.fmt.wrap_code(traceback.format_exc())
                await self.mng.debugSend(f"## Error \n> {ex}\n - while processing message\n" + trace, mc)

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onConnecting(self, transport_details):
        print("Connecting; transport details: {}".format(transport_details))
        return None  # ask for defaults

    def setupPipeChannel(self):
        import os, time

        pipe_path = bc.PIPE_CHANNEL_PATH
        if not os.path.exists(pipe_path):
            os.mkfifo(pipe_path)
        # Open the fifo. We need to open in non-blocking mode or it will stalls until
        # someone opens it for writting
        pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(pipe_fd) as pipe:
            while True:
                try:
                    message = pipe.read()
                except:
                    message = None
                if message:
                    print("Received: '%s'" % message)
                    self.queue.put_nowait(("Received PIPE: '%s'" % message, None))                     
                if message == "EXIT":
                    print("Exiting")
                    break

    async def process_queue(self):
        import time
        while True:
            message, context = await self.queue.get()
            await self.mng.debugSend(message, context)
            self.queue.task_done()

    async def start_http_server(self):
        self.app = web.Application()
        self.app.add_routes([
            web.post('/debugSend', self.http_debug_send),
            web.post('/messageSend', self.http_message_send),
            # now capture all request to `/langchain/*`
            web.get('/langchain/info', self.http_langsmith_info),
            web.post('/langchain{tail:.*}', self.http_langsmith_internal),
        ])
        runner = web.AppRunner(self.app)
        await runner.setup()
        self.site = web.TCPSite(runner, 'localhost', 8080)
        await self.site.start()
        
    async def http_langsmith_info(self, request):
        data = {
            "version":"0.2.31",
            "license_expiration_time": None,
            "batch_ingest_config": {
                 "scale_up_qsize_trigger":1000,
                 "scale_up_nthreads_limit":16,
                 "scale_down_nempty_trigger":4,
                 "size_limit":100,
                 "size_limit_bytes":20971520
            }
        }
        return web.json_response(data)

        
    async def http_langsmith_internal(self, request):
        data = await request.json()
        
        pretty = await self.fmt.wrap_code(json.dumps(data, indent=4))
        
        await self.mng.debugSend(pretty, None)
        return web.json_response({'status': 'message received'})
        
    async def http_message_send(self, request):
        data = await request.json()
        # query param 'token' is required
        if 'token' not in data or data['token'] != bc.INTERNAL_COMMUNICATION_SECRET:
            return web.json_response({'error': 'Invalid token'}, status=403)

        message = data['message']
        chat_id = data['chat_id']
        recipient_id = data['recipient_id']
        
        await self.mng.debugSend(message, None)
        # curl -d '{"message":"Hello world!"}' -H "Content-Type: application/json" -X POST http://localhost:8080/debugSend
        return web.json_response({'status': 'message received'})

    async def http_debug_send(self, request):
        data = await request.json()
        # query param 'token' is required
        if 'token' not in data or data['token'] != bc.INTERNAL_COMMUNICATION_SECRET:
            return web.json_response({'error': 'Invalid token'}, status=403)

        message = data['message']
        await self.mng.debugSend(message, None)
        # curl -d '{"message":"Hello world!"}' -H "Content-Type: application/json" -X POST http://localhost:8080/debugSend
        return web.json_response({'status': 'message received'})

    def onOpen(self):
        print("WebSocket connection open.")
        # fulsh the db on connection open
        print("Flushing db (per default on startup)")
        asyncio.ensure_future(self.db.flush())
        asyncio.ensure_future(self.db.getOrFetchBotUser())
        asyncio.ensure_future(self.mng.debugSend("Connected to server\n - Flushed db", None))
        asyncio.create_task(self.start_http_server())

        
    async def process_message(self, payload):
        data = json.loads(payload.decode('utf8'))
        data_type = data.get('type')
        data = data.get('data')
        if data_type == 'custom':
            action = data.get('action')
            payload = data.get('payload')
            await self.onProcessCustomMessage(action, payload)
        else:
            print("Unknown message type", data_type)

    def onMessage(self, payload, isBinary):
        if isBinary:
            raise Exception("NOT IMPLEMENTED! Binary message received: {0} bytes".format(len(payload)))
        asyncio.ensure_future(self.process_message(payload))


    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))
        try:
            asyncio.ensure_future(self.site.stop())
            asyncio.ensure_future(self.app.cleanup())
        except Exception as ex:
            print("Error stopping site", ex)
            
        raise Exception("Connection closed")