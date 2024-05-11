import sys

from agent.complete_json import complete_json, BaseTaskDescription
from agent.paralel_json_complete import json_complete_paralel
from agent.paralel_intend_and_extract import intend_extract_paralel_json
import json
import yaml
from datetime import datetime
import pathlib

cur_path = pathlib.Path(__file__).parent.resolve()
print("Current path:", cur_path)

def test_task_description():
    from agent.models import MODELS


    with open("tests/data/scientists_prompt.yaml") as f:
        data = yaml.safe_load(f)
    base_task_description = data["task"]

    tasks = []
    batch_size = 1
    for toggle in MODELS:
        model = toggle.model
        temp = base_task_description.get("temperature", 0.0)
        for _ in range(batch_size):
            tasks.append(BaseTaskDescription(**{
                **base_task_description,
                "temperature": temp,
                "model": model
            }))
            temp += 0.1
    
    out = json_complete_paralel(tasks)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    with open(f"tests/_reports/{timestamp}_scientists_json.json", "w") as f:
        f.write(json.dumps(out, indent=4))
        
def test_intend_extract():
    from agent.models import MODELS

    
    prompts = {
        "albert": "What is the birth date of Albert Einstein?",
        "current_weather": "What is the current weather in New York?",
        "tell_joke": "Tell me a joke.",
        "who_am_i": "Who is the current president of the United States?"
    }
    
    out = intend_extract_paralel_json(
        prompt=prompts["albert"],
        models=[mb.model for mb in MODELS],
        batch_size=1
    )

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    with open(f"tests/_reports/{timestamp}_test_intend.json", "w") as f:
        f.write(json.dumps(out, indent=4))

def tests_single_models_intend_response():
    #prompt = "What the weather in Bremen"
    prompt = "Do you know a funny joke?"
    out = intend_extract_paralel_json(
        prompt=prompt,
        models=["meta-llama/Meta-Llama-3-70B-Instruct"],
        batch_size=4
    )
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    with open(f"{cur_path}/_reports/{timestamp}_test_intend_meta_llama3_8b.json", "w") as f:
        f.write(json.dumps(out, indent=4))

        