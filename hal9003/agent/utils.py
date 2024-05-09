import openai
from .models import BackendConfig

def debug_log(message, model=None):
    prefix = f"[{model}] " if model else ">"
    print(f"{prefix} {message}")

def create_client(
    backend: BackendConfig
):
    client = openai.OpenAI(
        api_key=backend.api_key,
        base_url=backend.base_url
    )
    return client
