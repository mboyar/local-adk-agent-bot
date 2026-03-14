---
name: Google ADK Agent Creation & Troubleshooting
description: Instructions and best practices for creating, running, and troubleshooting Google ADK (Agent Development Kit) agents.
---

# Google ADK Agent Development

This skill provides comprehensive instructions on how to create, configure, and troubleshoot Google ADK (Agent Development Kit) agents.

## 1. Creating a Google ADK Agent
ADK agents are built around a core `Agent` object. The typical entrypoint is `agent.py`.

### Basic Agent Structure
```python
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

# Define custom tools
def my_custom_tool(param: str):
    """Description of what the tool does (used by the LLM)."""
    return f"Executed tool with {param}"

# Initialize the Root Agent
root_agent = Agent(
    model=LiteLlm(model='ollama_chat/qwen3:4b'),
    name='root_agent',
    description='A highly capable assistant.',
    instruction='''Answer user questions. 
If the user asks to do X, use the my_custom_tool tool.''',
    tools=[my_custom_tool]
)
```

### Key Components
- **Models**: ADK supports various models. When using Ollama locally via the LiteLLM proxy, use the `LiteLlm` adk class (e.g., `LiteLlm(model='ollama_chat/qwen3:4b')`) and ensure `OLLAMA_API_BASE` is set.
- **Instructions**: The system prompt given to the agent. Clearly list when tools should be utilized based on user intents.
- **Tools**: Define standard Python functions with robust docstrings and type hints. Do not forget to legally register them in the `tools` array of the Agent initialization.

## 2. Running the Agent API Server
Instead of executing `agent.py` directly, ADK provides a robust API server to host your agent interactively.

1. Ensure your `.env` is loaded so the models and tools have their credentials.
2. Launch the framework's native `api_server`:
   ```bash
   adk api_server --port 8000 --auto_create_session
   ```
   *Note: `--auto_create_session` allows automated communication bridges (like your Telegram bots) to initialize independent conversational chat sessions dynamically.*

## 3. ADK CLI Troubleshooting

### Context: "adk: command not found"
The most common error encountered is running `adk api_server` and receiving a `Command not found` error. 

**Root Cause 1:** The `adk` package is installed inside the local Python virtual environment (`.venv`), not globally on the system (like an apt package).

**Resolution 1:**
Always activate the virtual environment FIRST before starting the server or running any `adk` command:
```bash
source .venv/bin/activate
adk api_server --port 8000 --auto_create_session
```

**Root Cause 2 (Folder Rename):** You have activated the virtual environment but still get the error. This happens if the project folder was renamed *after* the virtual environment (`.venv`) was created (e.g., folder renamed from `local-adk-agent-bot` to `local_adk_agent_bot`). The `.venv/bin/activate` script hardcodes the absolute path to the virtual environment at the time it was created. Activating it prepends the *old* (non-existent) path to your bash `$PATH`.

**Resolution 2:**
Recreate the virtual environment so it picks up the true, current directory path.
```bash
deactivate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Missing Module Errors
If ADK fails to initialize complaining about missing tool imports:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Best Practices for AI Agents modifying ADK Code
- **Updating Tools**: When adding a new tool, define the function cleanly and do not forget to append it to the `tools=[...]` array in `agent.py`.
- **Modifying Instructions**: Whenever a tool is created, the agent's `instruction=` block must be updated to explicitly describe what context the LLM should invoke the tool under.
- **Shell Execution**: When needing to restart or verify the ADK server, ensure it is executed gracefully: `source .venv/bin/activate && adk ...`.
