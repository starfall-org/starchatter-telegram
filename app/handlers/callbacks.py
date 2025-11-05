import asyncio
import os

from ai.base import models
from database.client import Database
from database.models import (
    TelegramGroup,
    TelegramUser,
)
from pyrogram import Client, enums, filters, types
from sqlalchemy import select
from utils import is_chat_admin, is_chat_owner, is_owner
from config import OWNER_ID

db = Database()


@Client.on_callback_query(
    filters.regex(r"menu/")  # type: ignore
)
async def group_admin_menu_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    action = callback_query.data
    chat_id = callback_query.message.chat.id
    group = await db.get(TelegramGroup, id=chat_id)
    if group:
        user = await db.get(TelegramUser, id=callback_query.from_user.id)
        if not user:
            user = TelegramUser(
                id=callback_query.from_user.id,
                first_name=callback_query.from_user.first_name,
                username=callback_query.from_user.username,
            )
            await db.add(user)
            await db.commit()
        if user not in group.users:
            group.users.append(user)
            await db.commit()
        if not (
            await is_chat_owner(callback_query.from_user, callback_query.message.chat)
            or await is_chat_admin(
                callback_query.from_user, callback_query.message.chat
            )
            or await is_owner(callback_query.from_user)
        ):
            await callback_query.answer("You must be an admin to perform this action.")
            return
        if action == "menu/chatbot":
            cmd = select(TelegramGroup).where(TelegramGroup.id == chat_id)
            result = await db.execute(cmd)
            if result:
                group = result.scalars().first()
                if group:
                    group.disable_chatbot = ~group.disable_chatbot
                    await db.commit()
            await callback_query.answer("Chatbot disabled for this group.")
            await callback_query.message.edit_text(
                "Chatbot has been disabled for this group."
            )
        elif action == "menu/anti_spam":
            cmd = select(TelegramGroup).where(TelegramGroup.id == chat_id)
            result = await db.execute(cmd)
            if result:
                group = result.scalars().first()
                if group:
                    group.disable_anti_spam = ~group.disable_anti_spam
                    await db.commit()
                await callback_query.answer("Anti-Spam disabled for this group.")
                await callback_query.message.edit_text(
                    "Anti-Spam has been disabled for this group."
                )
        elif action == "menu/goodbye":
            await callback_query.answer("Goodbye! 👋")
            await callback_query.message.edit_text("Goodbye! 👋")
            await asyncio.sleep(3)
            await client.leave_chat(chat_id)


@Client.on_callback_query(
    filters.regex(r"openai/") & filters.user(OWNER_ID)  # type: ignore
)
async def select_model_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    model_id = str(callback_query.data).split("/")[1]
    all_models = models()
    markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    text=model.id,
                    callback_data=f"openai/{model.id}",
                )
            ]
            for model in all_models
        ]
    )
    os.environ["AGENT_MODEL"] = model_id
    await callback_query.answer(f"Selected model: `{model_id}`", show_alert=True)
    await callback_query.message.edit_text(
        f"Selected model: `{model_id}`", reply_markup=markup
    )
