from client import client
from telethon import events


@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.reply("Hello, I'm a bot! How can I help you?")
