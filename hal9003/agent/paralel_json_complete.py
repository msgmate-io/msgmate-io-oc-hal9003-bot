import time
import concurrent.futures
from agent.complete_json import BaseTaskDescription, complete_json
from tabulate import tabulate

def timed(func):
    def _w(*a, **k):
        then = time.time()
        res = func(*a, **k)
        elapsed = time.time() - then
        return elapsed, res
    return _w

def json_complete_paralel(
    task_descriptions: list[BaseTaskDescription],
    task_id: str = "paralel-try-0"
):
    task_by_id = {}
    for i, task_description in enumerate(task_descriptions):
        task_description.task_id = f"task-{i}/" + (task_description.task_id or task_description.model)
        task_by_id[task_description.task_id] = task_description.to_dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(task_descriptions)) as executor:
        futures = [executor.submit(timed(complete_json), task) for task in task_descriptions]

        results = [future.result() for future in futures]
        models_res = {}
        for elapsed, result in results:
            models_res[result.task_id] = {
                **(result.to_dict()),
                "elapsed": elapsed
            }

    table = []
    winners = []
    for task in models_res:
        res = models_res[task]
        if res["valid"] and res["parsable"]:
            winners.append(task)
        row = [task, len(res["response"]), res["parsable"], res["valid"], res["elapsed"], res["temperature"]]
        table.append(row)
    print(tabulate(table, headers=["Model", "Response length", "Parsable", "Valid json", "Time elapsed", "Temp"]))
        
    return {
        "task_descriptions": task_by_id,
        "results": models_res,
        "winners": winners,
        "task_id": task_id
    }