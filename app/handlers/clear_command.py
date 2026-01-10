import asyncio

from app.ai.text import localize
from pyrogram import Client, enums, filters, types
from agents import SQLiteSession

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(filters.command("clear"))  # type: ignore
async def clear_handler(client: Client, message: types.Message):
    """Clear conversation history"""
    if message.chat.id < 0:
        member = await message.chat.get_member(message.from_user.id)
        if member.status not in [
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.ADMINISTRATOR,
        ]:
            admin_text = await localize(
                "You must be an admin to use this command.",
                user_id=message.from_user.id,
            )
            await message.reply(admin_text, quote=True)
            return
    await message.reply_chat_action(enums.ChatAction.TYPING)
    chat_id = message.chat.id
    session = SQLiteSession(f"chat_{chat_id}", "conversations.sqlite")
    await session.clear_session()
    cleared_text = await localize(
        "__Conversation cleared.__",
        user_id=message.from_user.id,
    )
    msg = await message.reply(
        cleared_text,
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await asyncio.sleep(30)
    await msg.delete()
