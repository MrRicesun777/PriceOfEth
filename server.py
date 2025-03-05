from flask import Flask
import threading
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your existing main script functions
from main import main as telegram_bot_main

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def run_telegram_bot():
    asyncio.run(telegram_bot_main())

if __name__ == "__main__":
    # Start Flask server in one thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Run Telegram bot in main thread
    run_telegram_bot()
