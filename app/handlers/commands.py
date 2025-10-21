from ai.poem import get_poem
from ai.nsfw import gen_img
from config import OWNER_ID
from database.client import Database
from database.models import GroupMember, TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types
from utils import is_chat_admin, is_chat_owner, is_owner

db = Database()

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(filters.command(["start", "help"]))  # type: ignore
async def start(client: Client, message: types.Message):
    markup = types.InlineKeyboardMarkup([[button for button in basic_buttons]])
    await message.reply(
        "Welcome to StarChatter.\n\nAvailable commands:\n\n/image [prompt] - Generate an image (NSFW non-blocked).\n/poem [prompt] - Generate a poem.",
        reply_markup=markup,
    )


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
        group.users.append(user)
        member_link = GroupMember(
            user_id=user.id,
            group_id=group.id,
            is_admin=await is_chat_admin(message.from_user, message.chat),
            is_owner=await is_chat_owner(message.from_user, message.chat),
        )
        group.user_links.append(member_link)
        user.group_links.append(member_link)
        await db.commit()
    if not (
        await is_chat_owner(message.from_user, message.chat)
        or await is_chat_admin(message.from_user, message.chat)
        or await is_owner(message.from_user)
    ):
        await message.reply("You must be an admin to access the menu.")
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
            [button for button in basic_buttons],
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


@Client.on_message(filters.command(["poem", "tho"]))  # type: ignore
async def poem_handler(client: Client, message: types.Message):
    locale = None
    if message.command[0] == "/tho":
        locale = "vi"
    author = message.from_user.full_name
    hint = message.text.split(" ", 1)[1]
    await message.reply_chat_action(enums.ChatAction.TYPING)
    poem = await get_poem(hint, locale)
    await message.reply(
        f"```\n{poem['result']}\n```——————__**{author}**__———————",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await message.delete()


@Client.on_message(filters.command("image"))  # type: ignore
async def nsfw_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    prompt = message.text.split(" ", 1)[1]
    await message.reply_photo(
        await gen_img(prompt),
        caption=f"```\n{prompt}\n```",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await message.delete()
