import asyncio

from ai.text import localize
from database.local import local_db
from pyrogram import Client, enums, filters, types

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(filters.command(["start", "help"]))  # type: ignore
async def start(client: Client, message: types.Message):
    """Xử lý lệnh start/help"""
    markup = types.InlineKeyboardMarkup([[button for button in basic_buttons]])
    welcome_text = await localize(
        "Welcome to StarChatter.\n\nAvailable commands:\n\n/image [prompt] - Generate an image (NSFW non-blocked).\n/poem [prompt] - Generate a poem.",
        user_id=message.from_user.id,
    )
    await message.reply(welcome_text, reply_markup=markup)


@Client.on_message(filters.command("clear"))  # type: ignore
async def clear_handler(client: Client, message: types.Message):
    """Xóa lịch sử trò chuyện"""
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
    
    # Xóa conversation từ local database
    await local_db.delete_conversation(chat_id)
    
    cleared_text = await localize(
        "__Conversation cleared. The bot now forgets everything about you.__",
        user_id=message.from_user.id,
    )
    msg = await message.reply(
        cleared_text,
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await asyncio.sleep(30)
    await msg.delete()
