# My ADK Agent with Telegram and Ollama

This project integrates a Google ADK-based agent with a Telegram bot and uses a local LLM running on an Nvidia Orin Nano via Ollama.

## Prerequisites

* Python virtual environment (`../venv`)
* `python-telegram-bot` installed in your virtual environment (`../venv/bin/pip install python-telegram-bot`)
* SSH access to `orinnano`

## Architecture Overview

1. **Ollama on Orin Nano**: Runs the local LLM (`qwen3:4b`).
2. **ADK API Server**: Runs on your local machine (`localhost:8000`), hosting the `my_agent` logic.
3. **Telegram Bot**: Runs on your local machine, fetching messages from Telegram and proxying them to the ADK API Server.

---

## Step 1: Start Ollama on Orin Nano

The ADK agent expects the Ollama API to be reachable at `localhost:11434`. The easiest and most secure way to do this is via SSH Port Forwarding.

1. Open a terminal and run the following command to securely forward the Ollama port from `orinnano` to your local machine:

   ```bash
   ssh -L 11434:localhost:11434 orinnano
   ```

2. Once logged into the `orinnano`, start the `qwen3:4b` model (or the model you have specified in your `agent.py`):

   ```bash
   ollama run qwen3:4b
   ```

*(Alternative: If you expose the Ollama host natively via `OLLAMA_HOST=0.0.0.0 ollama serve` on the Orin Nano, make sure to `export OLLAMA_API_BASE="http://orinnano:11434"` on your local machine before starting the ADK API Server.)*

---

## Step 2: Start the ADK API Server

In a new terminal window on your local machine, run the ADK server using your virtual environment.

We pass the `--auto_create_session` flag so that the Telegram bot can dynamically create ADK sessions for every new Chat ID it encounters:

```bash
cd /home/mboyar/prj-home/google-agent-devkit/my_agent
../venv/bin/adk api_server --port 8000 --auto_create_session
```

---

## Step 3: Run the Telegram Bot

If you haven't already, acquire a `TELEGRAM_TOKEN` from [@BotFather](https://t.me/botfather) on Telegram.

Then, open a third terminal window, export your token, and start the python bot:

```bash
cd /home/mboyar/prj-home/google-agent-devkit/my_agent
export TELEGRAM_TOKEN="your_bot_token_here"
../venv/bin/python telegram_bot.py
```

You can now start messaging your bot on Telegram. The bot bridges communication directly to the `root_agent` executing against the Orin Nano!
