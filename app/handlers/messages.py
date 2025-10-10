from telethon import events, TelegramClient


def register(
    client: TelegramClient,
):
    @client.on(events.NewMessage(incoming=True))
    async def handle_incoming_message(event):
        # Handle incoming messages here
        pass
