"""Callback handlers for AI provider management."""

import os

from app.ai.base import models as get_models
from app.handlers.admin.owner import is_user_owner
from pyrogram import Client, enums, filters, types


@Client.on_callback_query(
    filters.regex(r"openai/")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def select_model_handler(client: Client, callback_query: types.CallbackQuery):
    """Select AI model"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    model_id = str(callback_query.data).split("/")[1]
    os.environ["AGENT_MODEL"] = model_id
    await callback_query.answer(f"Selected model: `{model_id}`", show_alert=True)
    await callback_query.message.delete()
    await callback_query.message.reply_to_message.delete()


@Client.on_callback_query(
    filters.regex(r"model/select/\d+")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def model_select_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle model selection via number button"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    model_num = int(parts[2])
    
    # Get the model name from the message or calculate from page
    # We need to track which model corresponds to which number
    # For now, use the stored models in the message
    
    all_models = await get_models()
    if 1 <= model_num <= len(all_models):
        model_id = all_models[model_num - 1]
        os.environ["AGENT_MODEL"] = model_id
        await callback_query.answer(f"Selected model: `{model_id}`", show_alert=True)
        await callback_query.message.delete()
        if callback_query.message.reply_to_message:
            await callback_query.message.reply_to_message.delete()
