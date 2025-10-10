from client import client
import handlers.commands
import handlers.messages
from database.client import create_all, Session


async def init():
    await create_all()
    
def main():
    client.start()
    print("Bot is running...")
    client.run_until_disconnected() 