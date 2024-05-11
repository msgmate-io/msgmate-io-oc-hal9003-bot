import openai
from agent import models


def debug_log(message, model=None):
    prefix = f"[{model}] " if model else ">"
    print(f"{prefix} {message}")

def create_client(
    backend: models.BackendConfig
):
    client = openai.OpenAI(
        api_key=backend.api_key,
        base_url=backend.base_url
    )
    return client

import json
from jsonschema import validate
from enum import Enum
from tabulate import tabulate
import concurrent.futures
from typing import Optional
from dataclasses import dataclass
from dataclasses import field


REFINEMENT_SCHEMA_PROMPT = """
Provide your answer in the following JSON format: 

{schema_description}

and respond with the JSON object only.
"""

@dataclass
class BaseTaskDescription:
    model: str = "meta-llama/Meta-Llama-3-70B-Instruct"
    prompt: str = ""
    schema: dict = field(default_factory=dict)
    schema_description: Optional[str] = None
    temperature: Optional[float] = None
    task_id: Optional[str] = None
    refinement_schema_prompt: Optional[str] = None
    
    def to_dict(self):
        return {
            "model": self.model,
            "prompt": self.prompt,
            "schema": self.schema,
            "schema_description": self.schema_description,
            "refinement_schema_prompt": self.refinement_schema_prompt,
            "temperature": self.temperature,
            "task_id": self.task_id
        }
        
@dataclass
class TaskResult:
    system_message: str
    response: str
    parsable: bool
    valid: bool
    parsed: dict
    temperature: Optional[float]
    task_id: str
    
    def to_dict(self):
        return {
            "system_message": self.system_message,
            "response": self.response,
            "parsable": self.parsable,
            "valid": self.valid,
            "parsed": self.parsed,
            "temperature": self.temperature,
            "task_id": self.task_id
        }


def complete_json(
    task: BaseTaskDescription
) -> TaskResult:
    """
    Complete a prompt according to a JSON schema and validate it.
    """
    
    debug_log("SELECTED MODEL:",task.model)
    model = models.get_model(task.model)
    client = create_client(model.client_config)
    
    assert task.schema_description or task.refinement_schema_prompt, "Either schema_description or refinement_schema_prompt must be provided."

    system_message = REFINEMENT_SCHEMA_PROMPT.format(
        schema_description=task.schema_description
    ) if task.schema_description else task.refinement_schema_prompt
    
    messages = [{
        "role": "system",
        "content": system_message    
    },
    {
        "role": "user",
        "content": task.prompt
    }]
    
    completion_params = {
        "model": model.model,
        "messages": messages,
    }
    
    if task.temperature:
        completion_params["temperature"] = task.temperature
    
    if model.supports_json:
        completion_params["response_format"] = {
            "type": "json_object"
        }

    response = client.chat.completions.create(
        **completion_params
    )
    
    parsable = False
    parsed = None
    try:
        parsed = json.loads(response.choices[0].message.content)
        parsable = True
    except Exception as e:
        debug_log("ERROR:" + str(e), model.model)
        
    valid = False
    if parsable:
        try:
            validate(parsed, task.schema)
            valid = True
        except Exception as e:
            debug_log("ERROR:" + str(e), model.model)
    
    res = response.choices[0].message.content
    
    return TaskResult(
        system_message=system_message,
        response=res,
        parsable=parsable,
        valid=valid,
        parsed=parsed,
        temperature=task.temperature,
        task_id=task.task_id or model.model
    )