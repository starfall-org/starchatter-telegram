from pyrogram import Client, enums, filters, types

from app.ai.nsfw import gen_img
from app.database.cloud import cloud_db
from app.database.local import local_db

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(filters.command("image"))  # type: ignore
async def nsfw_handler(client: Client, message: types.Message):
    """Generate image"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    prompt = message.text.split(" ", 1)[1]
    await message.reply_photo(
        await gen_img(prompt),
        caption=f"```\n{prompt}\n```",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await message.delete()
