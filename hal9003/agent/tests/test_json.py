import sys

sys.path.append('..')
from tims_agent_toolkit.complete_json import complete_json, BaseTaskDescription
from tims_agent_toolkit.models import MODELS
from tims_agent_toolkit.paralel_json_complete import json_complete_paralel
from tims_agent_toolkit.paralel_intend_and_extract import intend_extract_paralel_json
import json
import yaml
from datetime import datetime

def test_task_description():

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
    

test_intend_extract()