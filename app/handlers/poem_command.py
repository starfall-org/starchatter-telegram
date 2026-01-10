from app.ai.poem import get_poem
from app.database.cloud import cloud_db
from app.database.local import local_db
from pyrogram import Client, enums, filters, types

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(filters.command("poem"))  # type: ignore
async def poem_handler(client: Client, message: types.Message):
    """Generate poem"""
    locale = None
    author = message.from_user.full_name
    hint = message.text.split(" ", 1)[1]
    await message.reply_chat_action(enums.ChatAction.TYPING)
    poem = await get_poem(hint, locale)
    await message.reply(
        f"__{poem}__\n——————**{author}**———————",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
