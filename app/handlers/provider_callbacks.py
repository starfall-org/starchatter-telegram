"""Provider callback handler for AI provider management."""

import re

from pyrogram import Client, enums, filters, types
from sqlalchemy import select

from app.ai.base import get_provider_models
from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider
from app.handlers.owner import is_user_owner
from app.handlers.pagination import (
    ITEMS_PER_PAGE,
    create_models_keyboard,
    create_providers_keyboard,
)

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


@Client.on_callback_query(
    filters.regex(r"^provider/page/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_page_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider pagination callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    page = int(parts[2])
    await show_providers_list(client, callback_query.message, page, force_cloud=False)
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/back$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_back_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle back to providers list callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    await show_providers_list(client, callback_query.message, 0, force_cloud=False)
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/close$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_close_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle close providers list callback"""
    await callback_query.message.delete()
    if callback_query.message.reply_to_message:
        await callback_query.message.reply_to_message.delete()
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_number_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider number selection callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_num = int(parts[1])
    # Get all providers to calculate which one was selected
    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()

    if 1 <= provider_num <= len(providers):
        provider = providers[provider_num - 1]
        # Show provider actions for this specific provider
        await show_provider_actions(
            client, callback_query.message, provider, force_cloud=False
        )
    else:
        await callback_query.answer("Invalid provider number!", show_alert=True)
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/select/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_select_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider selection callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    # Set provider as default (write via cloud)
    await write_db.set_default_provider(provider)
    await callback_query.answer(
        f"Provider `{provider.name}` is now default!", show_alert=True
    )


@Client.on_callback_query(
    filters.regex(r"^provider/edit/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_edit_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider edit callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    default_provider = await read_db.get_default_provider()
    default_tag = (
        " ⭐ (Default)"
        if default_provider and provider.id == default_provider.id
        else ""
    )
    await callback_query.answer(
        f"**Edit Provider: {provider.name}**{default_tag}\n\n"
        f"URL: `{provider.base_url}`\n"
        f"API Key: `{provider.api_key[:10]}...`\n\n"
        f"⚠️ Edit functionality not implemented yet.",
        show_alert=True,
    )


@Client.on_callback_query(
    filters.regex(r"^provider/delete/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_delete_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider delete callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    # Delete provider (write via cloud)
    await write_db.delete(provider)
    await callback_query.answer(f"Provider `{provider.name}` deleted!", show_alert=True)
    await show_providers_list(client, callback_query.message, 0, force_cloud=False)


@Client.on_callback_query(
    filters.regex(r"^provider/models_/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_models_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle initial provider models callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    # Initial models view
    await show_provider_models(
        client, callback_query.message, provider.id, provider.name, 0
    )
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/models_/\d+/page/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_models_page_handler(
    client: Client, callback_query: types.CallbackQuery
):
    """Handle provider models pagination callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])
    page = int(parts[4])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    await show_provider_models(
        client, callback_query.message, provider.id, provider.name, page
    )
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider/models_/\d+/back$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_models_back_handler(
    client: Client, callback_query: types.CallbackQuery
):
    """Handle back from models to provider actions callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    # Back from models to provider actions
    await show_provider_actions(
        client, callback_query.message, provider, force_cloud=False
    )
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"^provider_models_select/\d+/\d+$")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_models_select_handler(
    client: Client, callback_query: types.CallbackQuery
):
    """Handle provider model selection callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    provider_id = int(parts[1])
    model_index = int(parts[2])

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    all_models = await get_provider_models(provider=provider)

    # Check if models list is empty
    if not all_models:
        await callback_query.answer("No models available!", show_alert=True)
        return

    # Validate model number (1-based indexing)
    # Convert from 1-based to 0-based indexing
    actual_model_index = model_index - 1
    selected_model = all_models[actual_model_index]
    # Save selected model to database
    await write_db.set_default_model("chat", provider.name, selected_model)
    await write_db.set_default_provider(provider)
    await callback_query.answer(f"Selected model: `{selected_model}`", show_alert=True)
    await show_provider_actions(client, callback_query.message, provider)
    await callback_query.answer()


async def show_providers_list(
    client: Client, message: types.Message, page: int = 0, force_cloud: bool = False
):
    """Display providers list with pagination."""

    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    # Use cloud database if force_cloud is True to get the latest default provider
    default_provider = await (
        cloud_db.get_default_provider()
        if force_cloud
        else read_db.get_default_provider()
    )

    if not providers:
        # Check if this is a reply to a command message
        if hasattr(message, "reply_to_message") and message.reply_to_message:
            await message.reply_to_message.reply(
                "No providers yet. Add a provider using:\n"
                "`/add_provider <name> <base_url> <api_key>`"
            )
            await message.delete()
        else:
            await message.edit_text(
                "No providers yet. Add a provider using:\n"
                "`/add_provider <name> <base_url> <api_key>`"
            )
        return

    # Prepare providers list with (id, name) tuples
    providers_list = [(p.id, p.name) for p in providers]

    # Calculate pagination
    total_pages = max(1, (len(providers_list) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(providers_list))
    page_providers = providers_list[start_idx:end_idx]

    # Create keyboard with numbered buttons
    markup = create_providers_keyboard(
        providers=page_providers,
        page=page,
        callback_prefix="provider",
        total_pages=total_pages,
    )

    # Build message with provider names and numbers
    start_num = page * ITEMS_PER_PAGE + 1
    provider_names = []
    for i, (provider_id, provider_name) in enumerate(page_providers):
        num = start_num + i
        is_default = default_provider and provider_id == default_provider.id
        prefix = "⭐ " if is_default else ""
        provider_names.append(f"`{num}`. {prefix}`{provider_name}`")

    providers_text = "\n".join(provider_names)
    new_text = f"**AI Providers** (Page {page + 1}/{total_pages})\n\n{providers_text}\n\nTap a number to select provider."

    # Check if message unchanged, skip edit_text call
    if message.text != new_text or str(message.reply_markup) != str(markup):
        await message.edit_text(new_text, reply_markup=markup)


async def show_provider_actions(
    client: Client,
    message: types.Message,
    provider: AIProvider,
    force_cloud: bool = False,
):
    """Display action buttons for a specific provider."""

    default_provider = await (
        cloud_db.get_default_provider()
        if force_cloud
        else read_db.get_default_provider()
    )

    # Create action buttons for this provider
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"🔹 {provider.name}",
                callback_data="noop",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="✅ Select",
                callback_data=f"provider/select/{provider.id}",
            ),
            types.InlineKeyboardButton(
                text="✏️ Edit",
                callback_data=f"provider/edit/{provider.id}",
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="🤖 Models",
                callback_data=f"provider/models_/{provider.id}",
            ),
            types.InlineKeyboardButton(
                text="🗑️ Delete",
                callback_data=f"provider/delete/{provider.id}",
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⬅️ Back",
                callback_data="provider/back",
            ),
        ],
    ]
    markup = types.InlineKeyboardMarkup(buttons)

    # Build message
    is_default = default_provider and provider.id == default_provider.id
    status = " ⭐ (Default)" if is_default else ""

    await message.edit_text(
        f"**Provider: {provider.name}**{status}\n\n"
        f"URL: `{provider.base_url}`\n"
        f"API Key: `{provider.api_key[:10]}...`\n\n"
        f"Use buttons below to manage this provider.",
        reply_markup=markup,
    )


async def show_provider_models(
    client: Client,
    message: types.Message,
    provider_id: int,
    provider_name: str,
    page: int,
):
    """Display models list of a provider with pagination using numbered buttons."""
    # Get provider object by ID
    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider_object = result.scalars().first()

    if not provider_object:
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="provider/back",
                ),
            ],
        ]
        markup = types.InlineKeyboardMarkup(buttons)
        await message.edit_text(
            "**Error**\n\nProvider not found!",
            reply_markup=markup,
        )
        return

    all_models = await get_provider_models(provider=provider_object)

    # Handle empty models list
    if not all_models:
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data=f"provider/models_/{provider_id}/back",
                )
            ]
        ]
        markup = types.InlineKeyboardMarkup(buttons)
        await message.edit_text(
            f"**Models for {provider_name}**\n\n"
            f"No models available.\n\n"
            f"Please check your provider settings or API connection.",
            reply_markup=markup,
        )
        return

    total_pages = max(1, (len(all_models) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(all_models))
    page_models = all_models[start_idx:end_idx]

    # Create numbered keyboard
    markup = create_models_keyboard(
        models=page_models,
        page=page,
        callback_prefix=f"provider_models_select/{provider_id}",
        total_pages=total_pages,
    )

    # Build message with model names
    start_num = page * ITEMS_PER_PAGE + 1
    model_names = []
    for i, model in enumerate(page_models):
        num = start_num + i
        model_names.append(f"`{num}`. `{model}`")

    models_text = "\n".join(model_names)

    await message.edit_text(
        f"**Models for {provider_name}** (Page {page + 1}/{total_pages})\n\n"
        f"{models_text}\n\n"
        f"Tap a number to select model.",
        reply_markup=markup,
    )
