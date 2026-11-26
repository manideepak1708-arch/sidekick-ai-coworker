# Sidekick Autonomous AI Co-Worker

New AI-assisted portfolio reconstruction (November 2026), not the original resume project. A bounded LangGraph worker/evaluator loop uses a local Ollama model, with Gradio for the interface and seven restricted tools: arithmetic, word count, uppercase, list/read/write text files, and a Playwright local-page interaction. No arbitrary Python REPL or unrestricted browser access is included. The evaluator is an LLM heuristic, not a correctness guarantee.

## Run locally
Python 3.11 recommended. Install [Ollama](https://ollama.com/), start it, and run `ollama pull mistral`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```
Open the local URL Gradio prints. Try “Calculate (12+5)*3”, “Create a note.txt with a short greeting”, or “Run the browser demo.” Inspect the tool trace. Files are limited to new `.txt` files in the workspace; existing files cannot be overwritten.

## Architecture
Task → Worker (LLM + tools) → Evaluator → Retry or finish (maximum 6 worker rounds). The worker receives previous tool outputs and evaluator feedback. Tool errors become visible evidence instead of crashing the loop.

## Test
`python -m pytest -q` runs mocked worker/evaluator and real restricted tool unit tests. Full graph, model and browser integration require locally installed dependencies and Ollama; not verified in the build environment.
