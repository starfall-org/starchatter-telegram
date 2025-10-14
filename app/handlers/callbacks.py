import asyncio

from config import OWNER_ID
from database.client import Database
from database.models import TelegramChannel, TelegramGroup, TelegramUser, LLMConfig, LLMProvider, LLMModel
from pyrogram import Client, enums, filters, types
from sqlalchemy import select

db = Database()


@Client.on_callback_query(filters.regex(r"^(_chatbot|_anti_spam|_goodbye)$")  # type: ignore
                          )
async def group_admin_menu_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    action = callback_query.data
    chat_id = callback_query.message.chat.id
    group = await db.get(TelegramGroup, id=chat_id)
    if group:
        if action == "disable_chatbot":
            cmd = select(TelegramGroup).where(TelegramGroup.id == chat_id)
            result = await db.execute(cmd)
            if result:
                group = result.scalars().first()
                if group:
                    group.disable_chatbot = ~group.disable_chatbot
                    await db.commit()
            await callback_query.answer("Chatbot disabled for this group.")
            await callback_query.message.edit_text("Chatbot has been disabled for this group.")
        elif action == "disable_anti_spam":
            cmd = select(TelegramGroup).where(TelegramGroup.id == chat_id)
            result = await db.execute(cmd)
            if result:
                group = result.scalars().first()
                if group:
                    group.disable_anti_spam = ~group.disable_anti_spam
                    await db.commit()
                await callback_query.answer("Anti-Spam disabled for this group.")
                await callback_query.message.edit_text("Anti-Spam has been disabled for this group.")
        elif action == "goodbye":
            await callback_query.answer("Goodbye! 👋")
            await callback_query.message.edit_text("Goodbye! 👋")
            await asyncio.sleep(3)
            await client.leave_chat(chat_id)


@Client.on_callback_query(filters.regex(r"^(config|edit_config)$")  # type: ignore
                          & filters.user(OWNER_ID)  # type: ignore
                          )
async def admin_menu_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    action = callback_query.data
    if action == "config":
        await callback_query.answer("LLM Config")
        await callback_query.message.edit_text("LLM Config Menu (to be implemented)")
    elif action == "edit_config":
        await callback_query.answer("Edit LLM Config")
        await callback_query.message.edit_text("Edit LLM Config Menu (to be implemented)")
