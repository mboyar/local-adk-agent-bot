import os
import httpx
import logging
import whisper
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADK_API_URL = "http://localhost:8000/run"

print("Loading Whisper Speech-to-Text model...")
whisper_model = whisper.load_model("base")

async def forward_to_adk(user_text, user_id, chat_id, update):
    payload = {
        "app_name": "my_agent",
        "user_id": user_id,
        "session_id": chat_id,
        "new_message": {"role": "user", "parts": [{"text": user_text}]}
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(ADK_API_URL, json=payload)
            response.raise_for_status()
            events = response.json()
            
            agent_response = ""
            for event in events:
                if event.get("author") == "root_agent":
                    parts = event.get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            agent_response += part["text"] + "\n"
            
            if agent_response:
                await update.message.reply_text(agent_response.strip())
            else:
                await update.message.reply_text("Agent processed the message but didn't return a text response.")
    except Exception as e:
        await update.message.reply_text(f"Error communicating with agent: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat_id)
    await forward_to_adk(user_text, user_id, chat_id, update)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat_id)
    
    processing_msg = await update.message.reply_text("🎙️ Transcribing voice message...")
    
    try:
        voice = await update.message.voice.get_file()
        file_path = f"voice_message_{user_id}.ogg"
        await voice.download_to_drive(file_path)
        
        result = whisper_model.transcribe(file_path)
        user_text = result["text"].strip()
        await processing_msg.edit_text(f"🎙️ *You said:* {user_text}", parse_mode='Markdown')
        
        await forward_to_adk(user_text, user_id, chat_id, update)
        
    except Exception as e:
        await processing_msg.edit_text(f"Failed to process voice message: {e}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your ADK agent bot. Send me a text or voice message and I will forward it to the agent.")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Please set TELEGRAM_TOKEN environment variable.")
        exit(1)
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("Telegram bot is running...")
    app.run_polling()
