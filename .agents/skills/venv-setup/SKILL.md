---
name: Python Virtual Environment Setup
description: Guide for setting up Python virtual environments and handling dependencies in the local ADK project.
---

# Python Virtual Environment Setup

This skill outlines how to bootstrap a new workspace or repair a missing environment within this ADK agent project.

## 1. Project Specifications
- **Python Version:** Python 3.10+
- **Environment Path:** `.venv` located at the project root (`/home/mboyar/prj-home/local_adk_agent_bot/.venv`)
- **Dependency File:** `requirements.txt`

## 2. Creating the Environment
If the `.venv` directory is missing, create it natively using the `venv` module:
```bash
python3 -m venv .venv
```

## 3. Activating the Environment
Before interacting with the project (running Python scripts like `telegram_bot.py` or ADK tools), the environment must be activated:
```bash
source .venv/bin/activate
```
This is critical for isolating the project dependencies from the host system securely.

## 4. Installing Dependencies
After activation, install the necessary project requirements. This typically includes packages like `google-adk`, `litellm`, `python-dotenv`, `pypdf`, and `requests`.

```bash
pip install -r requirements.txt
```

## 5. Agent Instructions
When an AI agent needs to execute Python code or install new packages:
1. **Never use global pip (`pip install <pkg>`).** Always ensure the `.venv` is targeted.
2. **Persistence:** If a new package is installed to fulfill a user request (e.g., `pip install python-dotenv`), the agent MUST append it to the `requirements.txt` file so the dependency tracks in version control.
3. **Execution Context:** When using executing scripts via the terminal, use short-circuit logic to activate the environment first: `source .venv/bin/activate && python3 agent.py`.
