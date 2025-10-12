from ai.base import BaseFactory
from database.client import ChatSession
from pyrogram import Client, filters, types  # pyright: ignore[reportPrivateImportUsage]


@Client.on_message(filters=filters.text)  # pyright: ignore[reportArgumentType]
async def start(client: Client, message: types.Message):
    await message.reply("Hello! I'm your bot. How can I assist you today?")
