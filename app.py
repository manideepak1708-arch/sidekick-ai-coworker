import os
import gradio as gr
from core import Ollama, Tools, build_graph

def solve(task):
    if not task.strip(): return 'Enter a task.', ''
    try:
        graph = build_graph(Ollama(os.getenv('OLLAMA_MODEL','mistral')), Tools())
        result = graph.invoke({'task':task,'history':[],'rounds':0}, config={'recursion_limit':20})
        status = 'Evaluator accepted' if result['verdict']=='accept' else 'Iteration limit reached; review manually'
        return status+'\n\n'+(result.get('answer') or 'No final answer generated.'), result.get('history',[])
    except Exception as e: return 'Unable to complete task: '+str(e), []

if __name__=='__main__':
    gr.Interface(fn=solve, inputs=gr.Textbox(label='Task',lines=4), outputs=[gr.Textbox(label='Answer',lines=8),gr.JSON(label='Tool trace')], title='Sidekick | Worker–Evaluator Agent', description='Local Ollama model, bounded retries and restricted tools.').launch(server_name='127.0.0.1')
