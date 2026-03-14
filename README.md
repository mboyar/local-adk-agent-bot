# My ADK Agent with Telegram and Ollama

This project integrates a Google ADK-based agent with a Telegram bot and uses a local LLM running on an Nvidia Orin Nano via Ollama.

## Features

- **Text messages** — forwarded to the ADK agent and answered by the LLM.
- **Voice messages** — transcribed locally with OpenAI Whisper, then forwarded to the agent.
- **Tool use** — the agent can shut down the Orin Nano, create files, fetch weather forecasts, and query PDF books.
- **Siemens Home Connect** — an included script (`siemens-home-connect-tool.py`) can fetch your appliances' door statuses.

## Prerequisites

- Python 3.10+
- `ffmpeg` — required by Whisper for audio processing (`sudo apt install ffmpeg`)
- SSH access to `orinnano` (for the shutdown tool)
- A Telegram bot token from [@BotFather](https://t.me/botfather)
- Ollama running the `qwen3:4b` model (on the local machine or a remote host)

## Setup

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_TOKEN=your-telegram-bot-token-here

# Set this if Ollama runs on a different machine (default: http://localhost:11434)
OLLAMA_API_BASE=http://localhost:11434
```

Both `agent.py` and `telegram_bot.py` load `.env` automatically via `python-dotenv`.

---

## Architecture Overview

1. **Ollama** — Runs the local LLM (`qwen3:4b`). Can be on the same machine or a remote host.
2. **ADK API Server** — Hosts the `root_agent` logic on `localhost:8000`.
3. **Telegram Bot** — Fetches messages from Telegram and proxies them to the ADK API Server.

---

## Running

### Step 1: Start Ollama

Ollama ships with a systemd service. Use it to start and manage the LLM server.

```bash
sudo systemctl start ollama
sudo systemctl enable ollama   # optional: start on boot
```

If the agent and Ollama run on **different machines**, configure Ollama to listen on all interfaces:

```bash
sudo systemctl edit ollama
```

Add the following, then save:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
```

Apply and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Then set `OLLAMA_API_BASE` in your `.env` on the agent machine:

```env
OLLAMA_API_BASE=http://<ollama-host-ip>:11434
```

### Step 2: Start the ADK API Server

```bash
source .venv/bin/activate
adk api_server --port 8000 --auto_create_session
```

The `--auto_create_session` flag lets the Telegram bot dynamically create ADK sessions for each Chat ID.

### Step 3: Run the Telegram Bot

```bash
source .venv/bin/activate
python telegram_bot.py
```

The bot reads `TELEGRAM_TOKEN` from your `.env` file — no need to export it manually.

---

## Project Structure

```
local-adk-agent-bot/
├── agent.py           # ADK agent definition with tools (shutdown, file creation, weather, PDF query)
├── telegram_bot.py    # Telegram bot that bridges messages to the ADK API server
├── siemens-home-connect-tool.py # Script to get the door status of Siemens appliances
├── __init__.py        # Package init (imports agent)
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
├── .env               # Your local config (git-ignored)
└── .gitignore
```

## License

This project is for personal use.
