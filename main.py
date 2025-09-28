import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("BOT_TOKEN")  # Read from environment variable
CHANNEL_ID = "@testfortestrender"  # Your channel username or chat_id

bot = Bot(token=TOKEN)

async def send_message_every_5min():
    while True:
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text="Hello from Render 🚀")
            print("Message sent successfully")
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(60)  # 5 minutes

if __name__ == "__main__":
    asyncio.run(send_message_every_5min())
    
