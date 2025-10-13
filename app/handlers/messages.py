from ai.base import BaseFactory
from pyrogram import Client, enums, filters, types

base = BaseFactory()


@Client.on_message(
    filters.text & (filters.private | (filters.mentioned | filters.reply)),
)
async def chatbot_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)

    content = await base.chat(message.text, message.chat.id, message.from_user.id)

    await message.reply(
        content or "Something went wrong!", reply_to_message_id=message.id
    )
