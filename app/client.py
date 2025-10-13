from pyrogram import Client

from .config import API_HASH, API_ID, BOT_TOKEN

client = Client(
    "starchatter",
    API_ID,
    API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "handlers"},
)
