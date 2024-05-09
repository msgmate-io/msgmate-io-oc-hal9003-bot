from typing import Optional
import json
from dataclasses import dataclass
from open_chat_api_client.models import Message, ChatResult
from bot.config import GLOBAL_DEBUG_CHAT_TITLE

@dataclass
class MessageContext:
    message: Message
    senderId: str
    chat: ChatResult

@dataclass
class ChatConfig:
    model: str
    context: int = 5
    systemPrompt: str = "You are a helpful assistant."
    
    def to_dict(self):
        return {
            "model": self.model,
            "context": self.context,
            "systemPrompt": self.systemPrompt
        }


class Manager:
    
    def __init__(self,bot=None, db=None):
        self.bot = bot
        self.db = db
        
    def syncSendCustomMessage(self, action, payload):
        return self.bot.sendMessage(json.dumps({
            'type': 'custom',
            'data': {
                'action': action,
                'payload': payload
            }
        }).encode('utf-8'), isBinary=False)
    
    async def sendCustomMessage(self, action, payload):
        # check if the chat is loaded in 'db'
        return self.syncSendCustomMessage(action, payload)
        
    async def debugSend(self, text, messageContext: Optional[MessageContext] = None, verbose=3):
        # TODO: Implement verbose levels
        debug_label = "DEBUG: "
        if messageContext:
            debug_label = f"DEBUG: Chat: {messageContext.chat.uuid}, Sender: {messageContext.senderId}\n"
        debug_label = await self.bot.fmt.wrap_code(debug_label)
        self.syncSendCustomMessage('send_message_chat_title', {
            'chat_title': GLOBAL_DEBUG_CHAT_TITLE,
            'text': debug_label + "\n" + text
        })
        
    async def sendPartialMessage(self, context: MessageContext, text):
        return await self.sendCustomMessage('partial_message', {
            'chat_id': context.chat.uuid,
            'recipient_id': context.senderId,
            'text': text
        })
        
    async def sendChatMessage(self, context: MessageContext, text):
        return await self.sendCustomMessage('send_message', {
            'chat_id': context.chat.uuid,
            'recipient_id': context.senderId,
            'text': text
        })
