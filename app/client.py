from telethon import TelegramClient
from .config import API_ID, API_HASH

client = TelegramClient("telegram-manager", API_ID, API_HASH)
