from ai.agent import AIAgent
from ai.nsfw import gen_img
from ai.poem import get_poem
from database.cloud import cloud_db
from database.local import local_db
from pyrogram import Client, enums, filters, types

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


@Client.on_message(
    (filters.mentioned & ~filters.new_chat_members | filters.private)
    & filters.incoming
    & ~filters.create(lambda _, __, m: m.text.startswith("/"))  # type: ignore
)
async def chatbot_handler(client: Client, message: types.Message):
    """Xử lý tin nhắn chatbot"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    agent = AIAgent()

    resp = await agent.run_chat(client, message)
    if resp:
        if len(resp) > 4000:
            for i in range(0, len(resp), 4000):
                await message.reply(
                    resp[i : i + 4000],
                    quote=True,
                    parse_mode=enums.ParseMode.MARKDOWN,
                )
        else:
            await message.reply(
                resp,
                quote=True,
                parse_mode=enums.ParseMode.MARKDOWN,
            )

    if not message.sender_chat:
        from database.models import TelegramUser

        user = await read_db.get(TelegramUser, id=message.from_user.id)
        user = user.scalars().first()
        if not user:
            await write_db.add(
                TelegramUser(
                    id=message.from_user.id,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    username=message.from_user.username,
                )
            )
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        from database.models import TelegramGroup

        group = await read_db.get(TelegramGroup, id=message.chat.id)
        group = group.scalars().first()
        if not group:
            await write_db.add(
                TelegramGroup(
                    id=message.chat.id,
                    title=message.chat.title,
                    username=message.chat.username,
                )
            )


@Client.on_message(filters.command("poem"))  # type: ignore
async def poem_handler(client: Client, message: types.Message):
    """Tạo thơ"""
    locale = None
    author = message.from_user.full_name
    hint = message.text.split(" ", 1)[1]
    await message.reply_chat_action(enums.ChatAction.TYPING)
    poem = await get_poem(hint, locale)
    await message.reply(
        f"__{poem}__\n——————**{author}**———————",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )


@Client.on_message(filters.command("image"))  # type: ignore
async def nsfw_handler(client: Client, message: types.Message):
    """Tạo hình ảnh"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    prompt = message.text.split(" ", 1)[1]
    await message.reply_photo(
        await gen_img(prompt),
        caption=f"```\n{prompt}\n```",
        reply_markup=types.InlineKeyboardMarkup([[button for button in basic_buttons]]),
    )
    await message.delete()
