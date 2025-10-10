from telethon import events, TelegramClient


def register(
    client: TelegramClient,
):
    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event: events.NewMessage.Event) -> None:
        await event.respond("Hello! I'm your bot. How can I assist you today?")

    @client.on(events.NewMessage(pattern="/help"))
    async def help_handler(event: events.NewMessage.Event) -> None:
        await event.respond(
            "Here are the commands you can use:\n/start - Start the bot\n/help - Get help information"
        )
