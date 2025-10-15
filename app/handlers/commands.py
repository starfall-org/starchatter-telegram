from config import OWNER_ID
from database.client import Database
from pyrogram import Client, enums, filters, types
from database.models import TelegramUser, TelegramGroup

db = Database()


@Client.on_message(filters.command(["start", "help"]))  # type: ignore
async def start(client: Client, message: types.Message):
    await message.reply("Welcome to StarChatter.")


@Client.on_message(filters.command("group_menu") & filters.group)  # type: ignore
async def group_menu(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    group = await db.get(TelegramGroup, id=message.chat.id)
    user = await db.get(TelegramUser, id=message.from_user.id)
    group = group.scalars().first()
    user = user.scalars().first()
    if not group:
        await db.add(
            TelegramGroup(
                id=message.chat.id,
                title=message.chat.title or "",
                username=message.chat.username,
            )
        )
        await db.commit()
        group = await db.get(TelegramGroup, id=message.chat.id)
        group = group.scalars().first()
    if not user:
        await db.add(
            TelegramUser(
                id=message.from_user.id,
                first_name=message.from_user.first_name or "",
                last_name=message.from_user.last_name or "",
                username=message.from_user.username or "",
            )
        )
        await db.commit()
        user = await db.get(TelegramUser, id=message.from_user.id)
        user = user.scalars().first()
    if user not in group.users:
        await message.reply("You must be a group admin to use this menu.", quote=True)
        return

    keyboard_markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    text=("Disable" if group.disable_chatbot else "Enable")
                    + " Chatbot",
                    callback_data="_chatbot",
                ),
                types.InlineKeyboardButton(
                    text=("Disable" if group.disable_anti_spam else "Enable")
                    + " Anti-Spam",
                    callback_data="_anti_spam",
                ),
            ],
            [types.InlineKeyboardButton(text="Goodbye", callback_data="_goodbye")],
        ]
    )

    await message.reply("Group Admin Menu:", reply_markup=keyboard_markup)


@Client.on_message(
    filters.command("menu") & filters.user(OWNER_ID)  # type: ignore
)
async def admin_menu(_: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    keyboard_markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(text="LLM Config", callback_data="config"),
                types.InlineKeyboardButton(text="Edit", callback_data="edit_config"),
            ],
            [
                types.InlineKeyboardButton(text="Providers", callback_data="providers"),
            ],
            [
                types.InlineKeyboardButton(
                    text="Add Provider", callback_data="add_provider"
                ),
                types.InlineKeyboardButton(
                    text="Delete Provider", callback_data="delete_provider"
                ),
            ],
            [
                types.InlineKeyboardButton(text="Channels", callback_data="channels"),
            ],
            [
                types.InlineKeyboardButton(
                    text="Add Channel", callback_data="add_channel"
                ),
                types.InlineKeyboardButton(
                    text="Delete Channel", callback_data="delete_channel"
                ),
            ],
            [
                types.InlineKeyboardButton(text="Groups", callback_data="groups"),
            ],
        ]
    )

    await message.reply("Admin Menu", reply_markup=keyboard_markup)
