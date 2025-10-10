from client import client
import handlers.commands
import handlers.messages
from database.client import create_all
import asyncio


def main():
    asyncio.create_task(create_all())
    client.start()
    print("Bot is running...")
    client.run_until_disconnected()
