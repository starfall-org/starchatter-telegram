import asyncio

from aiohttp import ClientSession
from config import OWNER_ID
from database.client import Database
from database.models import (
    LLMConfig,
    LLMModel,
    LLMProvider,
    TelegramGroup,
    TelegramUser,
)
from pyrogram import Client, enums, filters, types
from sqlalchemy import select
from utils import is_chat_admin, is_chat_owner, is_owner

db = Database()


@Client.on_callback_query(
    filters.regex(r"^(_chatbot|_anti_spam|_goodbye)$")  # type: ignore
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
        if action == "disable_chatbot":
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
        elif action == "disable_anti_spam":
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
        elif action == "goodbye":
            await callback_query.answer("Goodbye! 👋")
            await callback_query.message.edit_text("Goodbye! 👋")
            await asyncio.sleep(3)
            await client.leave_chat(chat_id)


@Client.on_callback_query(
    filters.regex(r"^config")  # type: ignore
    & filters.user(OWNER_ID)  # type: ignore
)
async def admin_menu_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await callback_query.answer("LLM Config")
    llm_config = await db.get(LLMConfig)
    if conf := llm_config.scalar_one_or_none():
        await callback_query.message.edit_text(
            f"**Current LLM Config:**\n**Provider:** {conf.provider.name}\n**Model:** {conf.model.name}\n**Instructions:** ```\n{conf.instructions}\n```",
            reply_markup=types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text="Edit Config", callback_data="edit_config"
                        )
                    ]
                ]
            ),
        )


@Client.on_callback_query(
    filters.regex(r"^providers$") & filters.group  # type: ignore
    | filters.user(OWNER_ID)
)
async def group_admin_menu(_: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await callback_query.answer("Providers")
    providers = await db.execute(select(LLMProvider))
    providers = providers.scalars().all()
    if not providers:
        await callback_query.message.edit_text(
            "No providers found. Please add a provider first.",
            reply_markup=types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text="Add Provider", callback_data="add_provider"
                        )
                    ]
                ]
            ),
        )
        return
    text = "**Available LLM Providers:**\n\n"
    button_list = []
    for provider in providers:
        text += f"**{provider.name}**\n"
        button_list.append(
            [
                types.InlineKeyboardButton(
                    text=f"Select {provider.name}",
                    callback_data=f"select_{provider.id}",
                )
            ]
        )
    button_list.append(
        [types.InlineKeyboardButton(text="Add Provider", callback_data="add_provider")]
    )
    await callback_query.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(button_list),
    )


@Client.on_callback_query(
    filters.regex(r"^/add_provider$") & filters.group  # type: ignore
    | filters.user(OWNER_ID)
)
async def add_provider_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await callback_query.answer("Add Provider")
    await callback_query.message.edit_text(
        "To add a new LLM provider, please send the provider details in the following format:\n\n"
        "`/add\n<Provider Name>\n<API Key>\n<Base URL>`\n\n"
        "For example:\n"
        "`/add\nOpenAI\nsk-xxxxxx\nhttps://api.openai.com/v1`\n\n",
    )

    provider_details = await callback_query.from_user.listen(filters.command("add"))
    if provider_details:
        details = provider_details.text.split("\n")
        if len(details) != 4:
            await callback_query.message.reply(
                "Invalid format. Please use the format mentioned above."
            )
            return
        _, name, api_key, base_url = details
        existing_provider = await db.execute(
            select(LLMProvider).where(LLMProvider.name == name)
        )
        if existing_provider.scalars().first():
            await callback_query.message.reply(
                f"Provider with name {name} already exists."
            )
            return
        new_provider = LLMProvider(
            name=name, api_key=api_key.strip(), base_url=base_url.strip()
        )
        await db.add(new_provider)
        await db.commit()
        await provider_details.delete()
        await callback_query.message.edit_text(
            f"Provider {name} added successfully.",
            reply_markup=types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text="View Providers", callback_data="providers"
                        )
                    ]
                ]
            ),
        )


@Client.on_callback_query(
    filters.regex(r"^select_(\d+)$") & filters.group  # type: ignore
    | filters.user(OWNER_ID)
)
async def select_provider_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await callback_query.answer("Select Provider")
    provider_id = int(str(callback_query.data).split("_")[1])
    provider = await db.get(LLMProvider, id=provider_id)
    if not provider:
        await callback_query.message.edit_text("Provider not found.")
        return
    models = await db.execute(
        select(LLMModel).where(LLMModel.provider_id == provider.id)
    )
    models = models.scalars().all()
    if not models:
        async with ClientSession() as http_client:
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            }
            async with http_client.get(
                f"{provider.base_url}/models", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    model_names = [
                        model["id"] for model in data.get("data", []) if "id" in model
                    ]
                    for model_name in model_names:
                        model = LLMModel(name=model_name, provider_id=provider.id)
                        await db.add(model)
                    await db.commit()
                    models = await db.execute(
                        select(LLMModel).where(LLMModel.provider_id == provider.id)
                    )
                    models = models.scalars().all()
                else:
                    await callback_query.message.edit_text(
                        "Failed to fetch models from the provider. Please check the API key and Base URL."
                    )
                    return

    text = f"**Available Models for {provider.name}:**\n\n"
    button_list = []
    for model in models:
        text += f"**{model.name}**\n"
        button_list.append(
            [
                types.InlineKeyboardButton(
                    text=f"Select {model.name}",
                    callback_data=f"set_model_{model.id}",
                )
            ]
        )
    await callback_query.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(button_list),
    )


@Client.on_callback_query(
    filters.regex(r"^set_model_(\d+)$") & filters.group  # type: ignore
    | filters.user(OWNER_ID)
)
async def set_model_handler(client: Client, callback_query: types.CallbackQuery):
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await callback_query.answer("Set Model")
    model_id = int(str(callback_query.data).split("_")[2])
    model = await db.get(LLMModel, id=model_id)
    if not model:
        await callback_query.message.edit_text("Model not found.")
        return
    llm_config = await db.get(LLMConfig)
    if conf := llm_config.scalar_one_or_none():
        conf.model_id = model.model_id
        conf.provider_id = model.provider_id
        await db.commit()
    else:
        new_conf = LLMConfig(model_id=model.model_id, provider_id=model.provider_id)
        await db.add(new_conf)
        await db.commit()
    await callback_query.message.edit_text(
        f"Model {model.name} has been set successfully.",
        reply_markup=types.InlineKeyboardMarkup(
            [[types.InlineKeyboardButton(text="View Config", callback_data="config")]]
        ),
    )
