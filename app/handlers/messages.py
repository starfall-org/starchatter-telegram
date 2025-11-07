from ai.agent import AIAgent
from ai.shield import detector
from database.client import Database
from database.models import TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types

db = Database()


@Client.on_message(
    filters.incoming & filters.group,  # type: ignore
    group=1,
)
async def spam_detector(client: Client, message: types.Message):
    def violation_detected(text):
        """
        Call it if violation detected
        """
        return True

    detected = await detector(message, tools=[violation_detected])
    if detected:
        agent = AIAgent()
        await message.reply_chat_action(enums.ChatAction.TYPING)
        await message.reply(
            await agent.run_chat(client, message, detected),
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN,
        )


@Client.on_message(
    (filters.mentioned | filters.private)
    & filters.incoming
    & ~filters.create(lambda _, __, m: m.text.startswith("/"))  # type: ignore
)
async def chatbot_handler(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    agent = AIAgent()

    resp = await agent.run_chat(client, message)
    if resp:
        await message.reply(
            resp,
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN,
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
                    username=message.from_user.username,
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
                    username=message.chat.username,
                )
            )
