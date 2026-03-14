---
name: Telegram Bot Integration Integration
description: Context and functionality of the Telegram bot connecting users to the ADK agent, handling text and voice transcriptions.
---

# Telegram Bot Integration 

This skill documents the primary interface connecting the user to the local Google ADK framework (`telegram_bot.py`).

## 1. Core Responsibilities
The script `telegram_bot.py` acts as a middleman and proxy:
1. Listens for user messages on a Telegram chat natively.
2. Extracts plain text and forwards it as JSON payloads to the locally running `adk api_server`.
3. Processes audio (`.ogg` voice messages), locally transcribes them using OpenAI's `whisper` model (`base`), and then forwards the transcribed string to the ADK agent as if it were a text message.
4. Reads the parsed JSON response from the ADK server back to the Telegram chat.

## 2. API Communication Bridge
The script forwards requests to the ADK API Server (typically running at `http://localhost:8000/run`):

- **Payload Structure**:
```json
{
    "app_name": "local_adk_agent_bot", // Defined by ADK_APP_NAME inside .env
    "user_id": "<telegram_user_id>",
    "session_id": "<telegram_chat_id>",
    "new_message": {
        "role": "user", 
        "parts": [{"text": "<transcribed_or_text_message>"}]
    }
}
```
*Note that the `session_id` directly inherits the `chat_id` from Telegram — this allows the ADK API server (which runs with `--auto_create_session`) to isolate and track conversations dynamically.*

## 3. Important Environment Variables
The script loads configuration via `python-dotenv`:
- `TELEGRAM_TOKEN`: The API credential mapping to the bot (obtained from BotFather).
- `ADK_API_URL`: The localhost target where the `adk api_server` receives POST requests.
- `ADK_APP_NAME`: Must match the directory/symlink name the ADK server exposes physically (default is `local_adk_agent_bot`).

## 4. Troubleshooting & Modifying
When making changes to the Telegram bot handling:
1. **Model Loads**: Whisper natively loads on thread initialization. Beware of heavy delayed start times (`print("Loading Whisper Speech-to-Text model...")`) before the `app.run_polling()` loop begins.
2. **Audio Dependencies**: `whisper` operations intrinsically require system-level package binaries (notably `ffmpeg`). If audio formatting fails, `sudo apt install ffmpeg` is likely missing.
3. **Execution context**: To test changes made to the bot, kill and restart the process explicitly inside `.venv`:
   ```bash
   source .venv/bin/activate
   python3 telegram_bot.py
   ```
4. **ADK Responses**: The ADK framework returns an array of events. The script is currently hardcoded to sequentially append `.text` parts matching `author == "root_agent"`.
