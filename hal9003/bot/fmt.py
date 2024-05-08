from open_chat_api_client.models import Message
from typing import Optional, Union
import json
import dataclasses
from datetime import datetime

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        elif isinstance(o, bytes):
            return o.decode('utf-8')
        elif hasattr(o, 'to_dict'):
            return o.to_dict()
        elif dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Exception):
            return str(o)
        return super().default(o)
    
    
class JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        ret = {}
        for key, value in obj.items():
            if key in {'created', 'updated'}:
                ret[key] = datetime.fromisoformat(value) 
            else:
                ret[key] = value
        return ret

class Formatter:
    
    async def openai_user_messages(self, messages: list[Message], bot_uuid="none", context: Optional[Union[int, str]] = 5):
        if isinstance(context, str):
            context = int(context)
        out_messages = []
        window_messages = messages
        print("Context", context)
        if context:
            window_messages = messages[-context:]
            
        for msg in window_messages:
            out_messages.append({
                "role": "user" if msg.sender != bot_uuid else "assistant",
                "content": msg.text
            })
        return out_messages
    
    async def remove_code(self, text):
        return text.replace("`", "")
    
    async def pretty_json(self, data):
        return await self.wrap_code(json.dumps(data, indent=4))

    async def wrap_code(self, text):
        prefix = ""
        if not text.startswith("```"):
            if not text.startswith("\n"):
                prefix = "```\n"
            else:
                prefix = "```"
        if not text.endswith("```"):
            if not text.endswith("\n"):
                suffix = "\n```"
            else:
                suffix = "```"
        return f"{prefix}{text}{suffix}"
