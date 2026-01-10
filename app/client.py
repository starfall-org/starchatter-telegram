from app.config import API_HASH, API_ID, BOT_TOKEN
from pyrogram import Client

client = Client(
    "starchatter",
    API_ID,
    API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "app/handlers"},
)
