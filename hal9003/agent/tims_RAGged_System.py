# following: https://drive.google.com/drive/u/1/folders/0AIA9qFIJf6kaUk9PVA
import concurrent.futures
import json
import time
# default factory field
from dataclasses import field
from dataclasses import dataclass
from jsonschema import validate
from agent.complete_json import get_client_for_model
from agent.models import get_model
import argparse
from typing import List

MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

## RAGged System

class RagNode:
    # some init params & a self.run(prompt, context) method
    name: str = None
    start_node: bool = False

    def __init__(
            self,
            name: str,
            start_node: bool = False,
            **kwargs
        ):
        self.name = name
        self.start_node = start_node
        self.create(**kwargs)
        
    def create(self, *args, **kwargs):
        pass
    
@dataclass
class YieldMessage:
    kind: str
    content: str

class NodeContext:
    message_history: List[dict] = []
    parent_results: dict = field(default_factory=dict)
    prompt: str = ""
    
    def __init__(self, message_history, prompt):
        self.message_history = message_history
        self.prompt = prompt
        
    def to_dict(self):
        return {
            "message_history": self.message_history,
            "parent_results": self.parent_results,
            "prompt": self.prompt
        }
        
    def copy(self):
        return NodeContext(**self.to_dict())

class RagEdge:
    # connect two RagNodes
    start: str = None
    end: str = None
    disabled: bool = False
    
    def __init__(self, start: RagNode, end: RagNode):
        self.start = start
        self.end = end
        
    def update_state(self, context):
        pass

def timed(func):
    def _w(*a, **k):
        then = time.time()
        res = func(*a, **k)
        elapsed = time.time() - then
        return elapsed, res
    return _w

class RagGraph:
    
    def __init__(
            self, 
            nodes: List[RagNode],
            edges: List[RagEdge]
        ):
        self.nodes = nodes
        self.edges = edges
        
    def get_start_node(self):
        for node in self.nodes:
            if node.start_node:
                return node
        return None
    
    def get_node(self, name):
        for node in self.nodes:
            if node.name == name:
                return node
        return None
    
    def get_sibling_nodes(self, node):
        siblings = []
        for edge in self.edges:
            if (not edge.disabled) and (edge.start == node.name):
                siblings.append(self.get_node(edge.end))
        return siblings
    
    def update_edges(self, start_node, context):
        for edge in self.edges:
            if edge.start == start_node.name:
                edge.update_state(context)
    
    def run_nodes(self, nodes, context):
        node_res = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = [executor.submit(timed(node.run), context) for node in nodes]

            results = [future.result() for future in futures]
            
            for result in results:
                elapsed, res = result
                format_time = "{:.2f}".format(elapsed)
                print("Elapsed:", format_time, "Result:", res.response)
                node_res[res.node_name] = res
        return node_res
    
    def run_subgraph(self, node, context):
        self.update_edges(node, context)
        siblings = self.get_sibling_nodes(node)
        print("Siblings:", siblings)
                
        # 3 - run all siblings in parallell
        print(f"Running {len(siblings)} siblings in parallell")
        res = self.run_nodes(siblings, context)
        context.parent_results = res

        for node_name, node_res in res.items():
            if len(node_res.yield_messages) > 0:
                for msg in node_res.yield_messages:
                    print(f"=====> Yielded message: {msg.content}")
            if node_res.forward:
                self.run_subgraph(self.get_node(node_name), context)

    def run(
            self,
            context: NodeContext,
        ):
        start_node = self.get_start_node()
        if start_node is None:
            raise Exception("No start node found.")
        
        print("Start node:", start_node)
        self.run_subgraph(start_node, context)
        
from dataclasses import dataclass
        
@dataclass
class RagNodeResult:
    node_name: str
    meta: dict = field(default_factory=dict)
    yield_messages: List[YieldMessage] = field(default_factory=list)
    response: dict = None
    forward: bool = True
    
    def to_dict(self):
        return {
            "node_name": self.node_name,
            "forward": self.forward,
            "response": self.response,
            "meta": self.meta
        }


# ***************************************************************
### Nodes:

class ParamExtractorNode(RagNode):
    base_prompt: str = """
You are a function parameter generating AI.
The User Intend AI has already identified the user intend as "{tool_name}".

So the user want to call the "{tool_name}" function, that that perform the following:
{tool_description}

The "{tool_name}" function has the following input schema:

{schema}

You should respond with a json object that looks e.g.: like this.

{schema_example}
  
Based on the field descriptions of the schema analyze the user input and generate the parameters.
""" 

    system_prompt = None
    schema = None
    schema_example = None
    tool_name = None
    tool_description = None
    model_name = MODEL
    
    def create(
            self,
            schema: dict,
            schema_example: dict,
            tool_name: str,
            tool_description: str,
            **kwargs
        ):
        
        self.schema = schema
        self.schema_example = schema_example
        self.tool_name = tool_name
        self.tool_description = tool_description
        self.model_name = kwargs.get("model", self.model_name)
        self.model = get_model(self.model_name)

        
    def run(
            self,
            context: NodeContext
        ):

        self.system_prompt = self.base_prompt.format(
            tool_name=context.prompt,
            schema=self.schema,
            tool_description=self.tool_description,
            schema_example=self.schema_example
        )
        
        messages = [{
            "role": "system",
            "content": self.system_prompt
        }, {
            "role": "user",
            "content": context.prompt
        }]
        
        print("Running ParamExtractorNode", messages)
        
        completion_params = {
            "model": self.model.model,
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.0,
        }

        client = get_client_for_model(self.model.model) # TODO effienctly lookup
        response = client.chat.completions.create(
            **completion_params
        )

        parsable = False
        parsed = None
        res = response.choices[0].message.content
        try:
            parsed = json.loads(res)
            parsable = True
        except Exception as e:
            print("ERROR:" + str(e), self.model.model)
            
        valid = False
        if parsable:
            try:
                validate(parsed, self.schema)
                valid = True
            except Exception as e:
                print("ERROR:" + str(e), self.model.model)

        print("RES", res) 
        
        return RagNodeResult(
            node_name=self.name,
            forward=valid,
            response=parsed,
            meta={
                "valid": valid,
                "parsable": parsable,
                "parsed": parsed,
            },
        )
        
class CasualResponseNode(RagNode):
    
    system_prompt = """You are an Higly intelligent and carismatic AI, you should respond presicely but still casual to the users prompt."""
    model_name = MODEL

    
    def create(self, system_prompt=None, **kwargs):
        self.system_prompt = system_prompt
        self.model_name = kwargs.get("model", self.model_name)
        self.model = get_model(self.model_name)

    
    def run(
            self,
            context: NodeContext
        ):

        messages = [{
            "role": "system",
            "content": self.system_prompt
        }, {
            "role": "user",
            "content": context.prompt
        }]
        
        print("Running ParamExtractorNode", messages)
        
        completion_params = {
            "model": self.model.model,
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.0,
        }

        client = get_client_for_model(self.model.model) # TODO effienctly lookup
        response = client.chat.completions.create(
            **completion_params
        )
        print("Running CasualResponseNode")
        
        res = response.choices[0].message.content
        
        return RagNodeResult(
            node_name=self.name,
            forward=True,
            response=res
        )

class ToolSelectorNode(RagNode):
    # a node that evaluates context results
    def run(
            self,
            context: NodeContext
        ):
        results = context.parent_results
        assert all([results[res].forward for res in results]), "Not all results are valid"
        
        parsed = {results[res].node_name: results[res].response for res in results}
        tool_map = {
            "web_search": "WebExtract",
            "memory_lookup": "MemoryLookup",
            "casual": "CasualResponse"
        }
        selected_tools = parsed["ToolUsageCategorizer"]["intends"]
        
        tool_params = {}
        for tool in selected_tools:
            tool_params[tool_map[tool]] = parsed[tool_map[tool]]
        
        return RagNodeResult(
            node_name=self.name,
            forward=True,
            response=parsed,
            yield_messages=[
                YieldMessage("info", f"Selected tools: {selected_tools}"),
                YieldMessage("info", f"Tool parameters: {tool_params}")
            ],
            meta={
                "parsed": parsed
            }
        )

nodes = [
    RagNode("StartNode", True),
    CasualResponseNode(
        "CasualResponse",
        system_prompt="You are an Higly intelligent and carismatic AI, you should respond presicely but still casual to the users prompt."
    ),
    ParamExtractorNode(
        "WebExtract",
        schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            }
        },
        tool_description="""The web search function will search the web for the given query, this can be especially useful when the user want to search for current information.""",
        schema_example="""{
        "query": "the users search query"
        }""",
        tool_name="web_search"
    ),
    ParamExtractorNode(
        "MemoryLookup",
        schema={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A clear meomory lookup description"
                }
            }
        },
        tool_description="""The memory lookup function will search the bots memory for the given description, this can be especially useful when the user want to recall a previous conversation or information.""",
        schema_example="""{
        "description": "The users memory lookup description"
        }""",
        tool_name="memory_lookup"
    ),
    ParamExtractorNode(
        "ToolUsageCategorizer",
        schema={
            "type": "object",
            "properties": {
                "intends": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["web_search", "memory_lookup", "casual"]
                    },
                    "description": "List of user intends"
                }
            }
        },
        schema_example="""{
        "intends": "List of user intends"
        }""",
        tool_name="intend_categorizer",
        tool_description="""
The tool usage categorizer function should list all intends the user has, here are the descriptions of the indends:

- web_search: The web search function will search the web for the given query, this can be especially useful when the user want to search for current information.
- memory_lookup: The memory lookup function will search the bots memory for the given description, this can be especially useful when the user want to recall a previous conversation or information.
- casual: The casual function is a casual conversation with the bot, this can be especially useful when the user want to have a casual conversation with the bot.
The casual function can only be used without the other functions intends.
""",
    ),
    ToolSelectorNode("ToolSelector"),
    RagNode("EndNode")
]

edges = [
    # Inital stage
    RagEdge(
        start="StartNode",
        end="WebExtract"
    ),
    RagEdge(
        start="StartNode",
        end="CasualResponse"
    ),
    RagEdge(
        start="StartNode",
        end="MemoryLookup"
    ),
    RagEdge(
        start="StartNode",
        end="ToolUsageCategorizer"
    ),
    # Process first stage results
    RagEdge(
        start="WebExtract",
        end="ToolSelector"
    ),
    RagEdge(
        start="ToolUsageCategorizer",
        end="ToolSelector"
    ),
    RagEdge(
        start="MemoryLookup",
        end="ToolSelector"
    ),
    RagEdge(
        start="CasualResponse",
        end="ToolSelector"
    )
]

def cmd_run():

    parser = argparse.ArgumentParser(description='Run the RAGged system')
    parser.add_argument("-p", type=str, help='The user prompt')
    
    args = parser.parse_args()

    test_run(args.p)


def test_run(prompt):
    
    graph = RagGraph(
        nodes=nodes,
        edges=edges
    )

    print("HI", graph)
    
    graph.run(
        context=NodeContext(
            message_history=[],
            prompt=prompt
        ),
    )
