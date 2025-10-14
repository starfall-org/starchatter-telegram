from ai.base import BaseFactory
from database.client import Database
from database.models import TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types

base = BaseFactory()
db = Database()


@Client.on_message(
    filters.text
    & (filters.private | (filters.mentioned | filters.reply))
    # pyright: ignore[reportArgumentType]
    & ~filters.create(lambda _, __, m: m.text.startswith("/"))
)
async def chatbot_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)

    content = await base.chat(message.text, message.chat.id)

    await message.reply(
        content or "Something went wrong!", reply_to_message_id=message.id
    )

    if not message.sender_chat:
        user = await db.get(TelegramUser, id=message.from_user.id)
        user = user.scalars().first()
        if not user:
            await db.add(
                TelegramUser(
                    id=message.from_user.id,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    username=message.from_user.username
                )
            )
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group = await db.get(TelegramGroup, id=message.chat.id)
        group = group.scalars().first()
        if not group:
            await db.add(
                TelegramGroup(
                    id=message.chat.id,
                    title=message.chat.title,
                    username=message.chat.username
                )
            )
