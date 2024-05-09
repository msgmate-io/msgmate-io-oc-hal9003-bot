from open_chat_api_client.api.messages import messages_send_create, messages_list
from open_chat_api_client.api.user import user_self_retrieve
from open_chat_api_client.api.chats import chats_settings_retrieve, chats_settings_create
from bot.manager import Manager, MessageContext, ChatConfig
from bot.fmt import Formatter, JSONDecoder, JSONEncoder
from open_chat_api_client.models import ChatResult, ChatSettings, SetChatTitleRequest, Message, UserSelf
import json
from typing import Optional
from bot import config as bc
from agent.models import get_model
import redis

class RedisEmulatedClient:

    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value):
        self.data[key] = value

    async def rpush(self, key, value):
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)

    async def lrange(self, key, start, end):
        if key not in self.data:
            return []
        return self.data[key][start:end]

    async def lset(self, key, index, value):
        if key not in self.data:
            return
        self.data[key][index] = value

    async def flushdb(self):
        self.data = {}

class DB:
    bot = None
    mng: Manager = None
    fmt = Formatter()

    def __init__(self, bot=None, redis_url=None, client=None):
        self.url = redis_url
        self.client = client
        self.db_client = None
        self.bot = bot
        self.mng = Manager(bot)
        
    async def flush(self):
        db = await self.get_or_create_client()
        await db.flushdb()
        
    async def get_or_create_client(self, emulated_client=(not bc.USE_REDIS)):
        if emulated_client and (not isinstance(self.db_client, RedisEmulatedClient)):
            self.db_client = RedisEmulatedClient()
            return self.db_client
        if self.db_client is None:
            pool = redis.ConnectionPool.from_url(self.url + "?decode_responses=true")
            self.db_client = redis.Redis.from_pool(pool)
        return self.db_client
    
    async def validateConfigOrReset(
            self, 
            chat_uuid, 
            settings: ChatSettings,
            mc: Optional[MessageContext] = None
        ) -> tuple[ChatSettings, ChatConfig]:
        try:
            config = ChatConfig(**settings.config)
        except Exception as ex:
            await self.mng.debugSend(f"## Chat settings found in db, failed to parse config\n - in chat {chat_uuid}\n> {ex}\n - **resetting config to defaults**", None, verbose=1)
            if mc:
                await self.mng.sendChatMessage(mc, f"Failed to parse chat settings config, resetting to defaults")
            config = ChatConfig(model=self.bot.ai_config[3])
            settings = await self.updateChatSettings(chat_uuid, ChatSettings(
                config=config.to_dict()
            ))
        return settings, config

    async def getOrCreateChatSettings(self, chat_uuid, mc: Optional[MessageContext] = None) -> tuple[ChatSettings, ChatConfig]:
        db = await self.get_or_create_client()
        settings = await db.get(f"chat:{chat_uuid}:settings")
        if not settings:
            await self.mng.debugSend(f"## Chat settings not found in db, fetching from server\n - in chat {chat_uuid}", None, verbose=2)
            # try to fetch current chat settings
            try:
                req = await chats_settings_retrieve.asyncio_detailed(chat_uuid=chat_uuid, client=self.client)
                await self.mng.debugSend(f"## Chat settings fetched from server\n - in chat {chat_uuid}\n{req.parsed}", None, verbose=2)
                settings = req.parsed
            except Exception as ex:
                await self.mng.debugSend(f"## Chat settings not found in db, failed to fetch from server\n - in chat {chat_uuid}\n> {ex}", None, verbose=1)
                settings = None
            if not settings:
                # initalize with default settings
                settings = await chats_settings_create.asyncio(chat_uuid=chat_uuid, body=SetChatTitleRequest(
                    config=ChatConfig(
                        model=bc.DEFAULT_MODEL,
                    ).to_dict()
                ), client=self.client)
                pretty_settings_json = await self.fmt.pretty_json(settings.to_dict())
                await self.mng.debugSend(f"## Chat settings not found in db, created\n - in chat {chat_uuid}\n{pretty_settings_json}", None, verbose=2)
            await db.set(f"chat:{chat_uuid}:settings", json.dumps(settings.to_dict()))
        else:
            settings = ChatSettings.from_dict(json.loads(settings))
            pretty_settings_json = await self.fmt.pretty_json(settings.to_dict())
            await self.mng.debugSend(f"## Chat settings found in db\n - in chat {chat_uuid}\n{pretty_settings_json}", None, verbose=3)
            
        settings, config = await self.validateConfigOrReset(chat_uuid, settings, mc=mc)
        return settings, config
    
    async def updateChatSettingsConfigKey(self, chat_uuid, key, value, mc: Optional[MessageContext] = None) -> tuple[ChatSettings, ChatConfig]:
        db = await self.get_or_create_client()
        _, cur_chat_config = (await self.getOrCreateChatSettings(chat_uuid))
        updated_settings = await chats_settings_create.asyncio(chat_uuid=chat_uuid, body=SetChatTitleRequest.from_dict(
            {"config" :{**cur_chat_config.to_dict(), **{key: value}}}
        ), client=self.client)
        await db.set(f"chat:{chat_uuid}:settings", json.dumps(updated_settings.to_dict()))
        pretty_settings_json = await self.fmt.wrap_code(json.dumps(updated_settings.to_dict(), indent=4))
        await self.mng.debugSend(f"## Chat settings updated in db\n - in chat {chat_uuid}\n{pretty_settings_json}", None, verbose=3)
        settings, config = await self.validateConfigOrReset(chat_uuid, updated_settings, mc=mc)
        return settings, config
    
    async def updateChatSettings(self, chat_uuid, settings: ChatSettings):
        db = await self.get_or_create_client()
        updated_settings = await chats_settings_create.asyncio(chat_uuid=chat_uuid, body=SetChatTitleRequest.from_dict(
            settings.to_dict()
        ), client=self.client)
        await db.set(f"chat:{chat_uuid}:settings", json.dumps(updated_settings.to_dict()))
        pretty_settings_json = await self.fmt.wrap_code(json.dumps(updated_settings.to_dict(), indent=4))
        await self.mng.debugSend(f"## Chat settings updated in db\n - in chat {chat_uuid}\n{pretty_settings_json}", None, verbose=3)
        return updated_settings
    
    async def getChatDefaultModel(self, chat_uuid):
        _, config = await self.getOrCreateChatSettings(chat_uuid)
        return config.model
    
    async def setChatDefaultModel(self, chat_uuid, model):
        db = await self.get_or_create_client()
        await db.set(f"chat:{chat_uuid}:model", model)
    
    async def addChatMessage(self, chat_uuid, message: Message):
        db = await self.get_or_create_client()
        await db.rpush(f"chat:{chat_uuid}:messages", json.dumps(message.to_dict()))
        
    async def getOrFetchBotUser(self) -> UserSelf:
        db = await self.get_or_create_client()
        user = await db.get("bot:user")
        if not user:
            user = await user_self_retrieve.asyncio(client=self.client)
            await db.set("bot:user", json.dumps(user.to_dict()))
            pretty_user_json = await self.fmt.wrap_code(json.dumps(user.to_dict(), indent=4))
            await self.mng.debugSend(f"## Bot user not found in db, created\n - self user {user.uuid}\n{pretty_user_json}", None, verbose=2)
        else:
            user = UserSelf.from_dict(json.loads(user))
            pretty_user_json = await self.fmt.wrap_code(json.dumps(user.to_dict(), indent=4))
            await self.mng.debugSend(f"## Bot user found in db\n - self user {user.uuid}\n{pretty_user_json}", None, verbose=3)
        return user
    
    async def getOrFetchChatMessages(
            self, 
            chat_uuid, 
            incoming_message: Message,
            min_context: int = 5
        ) -> list[Message]:
        db = await self.get_or_create_client()
        range = await db.lrange(f"chat:{chat_uuid}:messages", 0, -1)
        

        range = range or []
        prev_messages = [Message.from_dict(json.loads(msg)) for msg in range]
        prev_msg_ids = [msg.uuid for msg in prev_messages]
        
        # for all indexes with 'tmp-' we generate a hash of the text and check if it matches the incoming message
        import hashlib
        tmp_msg_shas = {hashlib.sha256(msg.text.encode('utf-8')).hexdigest(): (msg.uuid, i) for i, msg in enumerate(prev_messages) if msg.uuid.startswith('tmp-')}
        all_tmp_msg_shas = list(tmp_msg_shas.keys())

        messages = await messages_list.asyncio(
            chat_uuid=chat_uuid,
            client=self.client,
            page_size=min_context
        )
        fetched_msgs = list(reversed(messages.results))
        for msg in fetched_msgs:
            msg_sha = hashlib.sha256(msg.text.encode('utf-8')).hexdigest()
            if msg_sha in all_tmp_msg_shas:
                tmp_msg_uuid, tmp_msg_index = tmp_msg_shas[msg_sha]
                prev_messages[tmp_msg_index] = msg
                prev_msg_ids[tmp_msg_index] = msg.uuid
                del tmp_msg_shas[msg_sha]
                await db.lset(f"chat:{chat_uuid}:messages", tmp_msg_index, json.dumps(msg.to_dict()))
                continue
            prev_id_pos = prev_msg_ids.index(msg.uuid) if msg.uuid in prev_msg_ids else -1
            if prev_id_pos != -1:
                await db.lset(f"chat:{chat_uuid}:messages", prev_id_pos, json.dumps(msg.to_dict()))
                prev_messages[prev_id_pos] = msg
            else:
                await db.rpush(f"chat:{chat_uuid}:messages", json.dumps(msg.to_dict()))
                prev_messages.append(msg)
                prev_msg_ids.append(msg.uuid)
        
        # check if the incoming message is already in the list
        incoming_message_index = prev_msg_ids.index(incoming_message.uuid) if (incoming_message.uuid in prev_msg_ids) else -1
        if incoming_message_index != -1:
            await db.lset(f"chat:{chat_uuid}:messages", incoming_message_index, json.dumps(incoming_message.to_dict()))
            prev_messages[incoming_message_index] = incoming_message
        else:
            await db.rpush(f"chat:{chat_uuid}:messages", json.dumps(incoming_message.to_dict()))
            prev_messages.append(incoming_message)

        messages = prev_messages

        pretty_updated_messages = await self.fmt.wrap_code(json.dumps([
            msg.to_dict() for msg in messages
        ], indent=4))
        await self.mng.debugSend(f"## Retrieving message from db\n - in chat {chat_uuid}\n{pretty_updated_messages}", None, verbose=3)
        return messages
    
    async def getChat(self, chat_uuid) -> Optional[ChatResult]:
        db = await self.get_or_create_client()
        chat = await db.get(f"chat:{chat_uuid}:data") or "null"
        data = json.loads(chat)
        return ChatResult.from_dict(data) if data else None
    
    async def setChat(self, chat_uuid, data: ChatResult):
        db = await self.get_or_create_client()
        await db.set(f"chat:{chat_uuid}:data", json.dumps(data, cls=JSONEncoder))
