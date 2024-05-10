from agent.complete_json import BaseTaskDescription
from agent.paralel_json_complete import json_complete_paralel
import json
import yaml
import pathlib


cur_path = pathlib.Path(__file__).parent.resolve()
print("Current path:", cur_path)


def get_intend_task(
    prompt: str,
    model: str,
    task_id: str
) -> BaseTaskDescription:

    with open(f"{cur_path}/prompts/user_intend_v0.3.yaml") as f:
        data = yaml.safe_load(f)
    
    return BaseTaskDescription(**{
        **data,
        'model': model,
        "prompt": prompt,
        "task_id": task_id
    })

def get_tools(
    prompt: str,
    model: str,
    task_id: str
) -> list[BaseTaskDescription]:
    with open(f"{cur_path}/prompts/tools_v0.2.yaml") as f:
        data = yaml.safe_load(f)
        
    tool_tasks = []
    for tool in data["tools"]:
        task_desc = BaseTaskDescription(
            prompt=prompt,
            schema=tool["schema"],
            task_id=task_id + f"/{tool['name']}",
            model=model,
            refinement_schema_prompt=data["base_prompt"].format(
                tool_name=tool["name"],
                schema=json.dumps(tool["schema"], indent=4),
                schema_example=tool["schema_example"]
            )
        )
        tool_tasks.append(task_desc)
    
    return data, tool_tasks

def intend_extract_paralel_json(
    prompt: str,
    models: list[str],
    batch_size: int = 3
):
    intend_tasks = []
    extraction_tasks = []
    
    for i in range(batch_size):
        for model in models:
            intend_tasks.append(get_intend_task(prompt, model, f"{model}/intend"))
            tool_data, tools = get_tools(prompt, model, f"{model}/extract")
            extraction_tasks.extend(tools)
            
    tasks = intend_tasks + extraction_tasks
    out = json_complete_paralel(tasks)
    
    intends = []
    tool_winners = []
    tool_pick_counts = {tool["name"]: 0 for tool in tool_data["tools"]}
    for task_id in out["winners"]:
        if "/intend" in task_id:
            intends.append({
                "task_id": task_id,
                "parsed": out["results"][task_id]["parsed"]
            })
            tool_pick_counts[out["results"][task_id]["parsed"]["intend"]] += 1
        elif "/extract" in task_id:
            tool_winners.append({
                "task_id": task_id,
                "tool": task_id.split("/")[-1],
                "parsed": out["results"][task_id]["parsed"]
            })
            
    print("Intends:", intends)
    most_picked_tool = max(tool_pick_counts, key=tool_pick_counts.get)
    print("Most picked tool:", most_picked_tool)
    extraction_for_tool = None
    for tool_winner in tool_winners:
        if tool_winner["tool"] == most_picked_tool:
            extraction_for_tool = tool_winner
            break
    print("Extraction for tool:", extraction_for_tool)
    out["tool_pick"] = most_picked_tool
    out["extraction_pick"] = extraction_for_tool
    return out