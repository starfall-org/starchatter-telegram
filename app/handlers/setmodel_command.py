from app.handlers.owner import is_user_owner
from pyrogram import Client, enums, filters, types

from app.database.local import local_db as read_db


@Client.on_message(
    filters.command("setmodel")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def set_model_command_handler(client: Client, message: types.Message):
    """Set default model for features (chat, translate)"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    buttons = [
        [
            types.InlineKeyboardButton(
                text="💬 Chat", callback_data="setmodel/feature/chat"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🌐 Translate", callback_data="setmodel/feature/translate"
            )
        ],
    ]
    markup = types.InlineKeyboardMarkup(buttons)

    # Show current models
    chat_model = await read_db.get_default_model("chat")
    translate_model = await read_db.get_default_model("translate")

    current_info = ""
    if chat_model:
        current_info += f"💬 Chat: `{chat_model.provider_name}/{chat_model.model}`\n"
    if translate_model:
        current_info += (
            f"🌐 Translate: `{translate_model.provider_name}/{translate_model.model}`\n"
        )

    if current_info:
        current_info = "**Current models:**\n" + current_info + "\n"

    await message.reply(
        f"{current_info}**Select Feature**\n\nChoose a feature to set default model:",
        reply_markup=markup,
        quote=True,
    )
