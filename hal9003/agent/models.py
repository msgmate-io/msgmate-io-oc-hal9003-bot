from dataclasses import dataclass
from bot import config as bc

@dataclass
class Backends:
    OPENAI = "openai"
    DEEPINFRA = "deepinfra"

@dataclass
class BackendConfig:
    api_key: str
    name: str
    base_url: str = None

@dataclass
class ModelBackend:
    model: str
    supports_json: bool
    supports_tools: bool
    supports_functions: bool
    client_config: BackendConfig
    
BACKENDS = {
    Backends.OPENAI: BackendConfig(
        name=Backends.OPENAI,
        api_key=bc.OPENAI_API_KEY,
        base_url=None
    ),
    Backends.DEEPINFRA: BackendConfig(
        name=Backends.DEEPINFRA,
        api_key=bc.DEEPINFRA_API_KEY,
        base_url="https://api.deepinfra.com/v1/openai"
    )
}

MODELS = [
    ModelBackend(
        model="meta-llama/Meta-Llama-3-70B-Instruct",
        supports_json=False,
        supports_tools=False,
        supports_functions=False,
        client_config=BACKENDS[Backends.DEEPINFRA]
    ),
    ModelBackend(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        supports_json=False,
        supports_tools=False,
        supports_functions=False,
        client_config=BACKENDS[Backends.DEEPINFRA]
    ),
    ModelBackend(
        model="databricks/dbrx-instruct",
        supports_json=False,
        supports_tools=False,
        supports_functions=False,
        client_config=BACKENDS[Backends.DEEPINFRA]
    ),
    ModelBackend(
        model="cognitivecomputations/dolphin-2.6-mixtral-8x7b",
        supports_json=False,
        supports_tools=False,
        supports_functions=False,
        client_config=BACKENDS[Backends.DEEPINFRA]
    ),
    ModelBackend(
        model="gpt-3.5-turbo",
        supports_json=False,
        supports_tools=True,
        supports_functions=True,
        client_config=BACKENDS[Backends.OPENAI]
    ),
    ModelBackend(
        model="gpt-4-turbo",
        supports_json=False,
        supports_tools=True,
        supports_functions=True,
        client_config=BACKENDS[Backends.OPENAI]
    )
]

def get_model(model_name):
    for model in MODELS:
        if model.model == model_name:
            return model
    return None