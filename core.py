"""Local-model worker/evaluator and restricted demonstration tools."""
import ast
import json
import operator
from pathlib import Path
from typing import TypedDict
import requests

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod, ast.USub: operator.neg,
       ast.UAdd: operator.pos}

def calculate(expression):
    if len(expression) > 120:
        raise ValueError('Expression too long')
    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e10: raise ValueError('Number too large')
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            value = OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
            if abs(value) > 1e15: raise ValueError('Result too large')
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](evaluate(node.operand))
        raise ValueError('Only arithmetic is allowed')
    return evaluate(ast.parse(expression, mode='eval').body)

class Tools:
    def __init__(self, root='workspace'):
        self.root = Path(root).resolve()
        self.root.mkdir(exist_ok=True, parents=True)
    def path(self, name):
        p = (self.root / name).resolve()
        if p.parent != self.root or p.suffix != '.txt':
            raise ValueError('Only .txt files directly inside workspace are allowed')
        return p
    def run(self, name, args):
        if not isinstance(args, dict): raise ValueError('Arguments must be an object')
        if name == 'calculate': return str(calculate(args['expression']))
        if name == 'word_count': return str(len(args['text'].split()))
        if name == 'uppercase': return args['text'][:5000].upper()
        if name == 'list_files': return '\n'.join(p.name for p in self.root.glob('*.txt') if p.is_file())
        if name == 'read_file':
            with self.path(args['name']).open(encoding='utf-8') as f: return f.read(12000)
        if name == 'write_file':
            p = self.path(args['name'])
            with p.open('x', encoding='utf-8') as f: f.write(args['text'][:12000])
            return f'Created {p.name}'
        if name == 'browser_demo':
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_content('<h1>Sidekick demo</h1><button onclick="this.textContent=\'Clicked\'">Run</button>')
                    page.get_by_role('button', name='Run').click()
                    return page.get_by_role('button').inner_text()
                finally: browser.close()
        raise ValueError('Unknown tool')

TOOL_SPEC = '''calculate {expression}; word_count {text}; uppercase {text}; list_files {}; read_file {name}; write_file {name,text} (new .txt only); browser_demo {} (local demo only).'''

class State(TypedDict, total=False):
    task: str
    history: list
    answer: str
    verdict: str
    feedback: str
    rounds: int

class Ollama:
    def __init__(self, model='mistral', url='http://localhost:11434'):
        self.model, self.url = model, url.rstrip('/')
    def __call__(self, system, payload):
        response = requests.post(self.url+'/api/chat', json={'model':self.model,'stream':False,'format':'json','messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(payload)}]}, timeout=120)
        response.raise_for_status()
        result = json.loads(response.json()['message']['content'])
        if not isinstance(result, dict): raise ValueError('Model must return a JSON object')
        return result

def worker_step(state, model, tools):
    history = list(state.get('history', []))
    result = model('You are a worker. Return JSON {"tool":"name","args":{}} to use one tool or {"answer":"final answer"}. Tools: '+TOOL_SPEC, {'task':state['task'],'history':history,'feedback':state.get('feedback','')})
    answer = str(result.get('answer',''))
    if 'tool' in result:
        try: output = tools.run(result['tool'], result.get('args',{}))
        except Exception as e: output = 'Tool error: '+str(e)
        history.append({'tool':result['tool'],'output':output})
        answer = ''
    return {'history':history,'answer':answer,'rounds':state.get('rounds',0)+1}

def evaluator_step(state, model):
    if not state.get('answer'): return {'verdict':'retry','feedback':'Use the tool result to continue.'}
    result = model('Review answer against task and tool evidence. Return JSON {"verdict":"accept" or "retry","feedback":"reason"}.', {'task':state['task'],'answer':state['answer'],'history':state.get('history',[])})
    return {'verdict':'accept' if result.get('verdict')=='accept' else 'retry','feedback':str(result.get('feedback',''))}

def route(state):
    return 'end' if state['verdict']=='accept' or state['rounds']>=6 else 'worker'

def build_graph(model, tools):
    from langgraph.graph import StateGraph, START, END
    graph = StateGraph(State)
    graph.add_node('worker', lambda s: worker_step(s, model, tools))
    graph.add_node('evaluator', lambda s: evaluator_step(s, model))
    graph.add_edge(START,'worker'); graph.add_edge('worker','evaluator')
    graph.add_conditional_edges('evaluator',route,{'worker':'worker','end':END})
    return graph.compile()
