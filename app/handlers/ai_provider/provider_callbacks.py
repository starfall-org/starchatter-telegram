"""Provider callback handler for AI provider management."""

from pyrogram import Client, enums, filters, types

from app.ai.base import models as get_models
from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider
from app.handlers.admin.owner import is_user_owner
from app.handlers.ai_provider.pagination import (
    ITEMS_PER_PAGE,
    create_models_keyboard,
    create_provider_actions_keyboard,
    create_providers_keyboard,
)

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


@Client.on_callback_query(
    filters.regex(r"provider/")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle provider management callback"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")

    # Check if this is a number-only callback (handled by provider_number_handler_v2)
    if len(parts) == 2 and parts[1].isdigit():
        return

    # Handle variable number of parts
    action = parts[1]
    provider_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    # Extract additional args if present (for models/{provider_id}/{model} or models_page/{provider_id}/{page})
    extra_args = parts[3:] if len(parts) > 3 else []

    if action == "list" and provider_id is None:
        # Show providers list with pagination
        await show_providers_list(client, callback_query.message, 0)
        return

    if action == "list_page" and provider_id is not None:
        # Pagination callback: provider/list_page/{page}
        page = provider_id
        await show_providers_list(client, callback_query.message, page)
        return

    if action == "list_back" or action == "back":
        # Back from provider details to list
        await show_providers_list(client, callback_query.message, 0)
        return

    if provider_id is None:
        await callback_query.answer("Invalid callback!", show_alert=True)
        return

    # Get provider from database (read from local)
    from sqlalchemy import select

    result = await read_db.execute(
        select(AIProvider).where(AIProvider.id == provider_id)
    )
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    if action == "select":
        # Set provider as default (write via cloud)
        await write_db.set_default_provider(provider)
        await callback_query.answer(
            f"Provider `{provider.name}` is now default!", show_alert=True
        )
        # Refresh message
        await show_providers_list(client, callback_query.message, 0)

    elif action == "edit":
        # Show edit form for provider details
        # For now, just show the provider details with a back button
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="provider/list_back",
                ),
            ],
        ]
        markup = types.InlineKeyboardMarkup(buttons)
        default_provider = await read_db.get_default_provider()
        default_tag = (
            " ⭐ (Default)"
            if default_provider and provider.id == default_provider.id
            else ""
        )
        await callback_query.message.edit_text(
            f"**Edit Provider: {provider.name}**{default_tag}\n\n"
            f"URL: `{provider.base_url}`\n"
            f"API Key: `{provider.api_key[:10]}...`\n\n"
            f"⚠️ Edit functionality not implemented yet.",
            reply_markup=markup,
        )

    elif action == "delete":
        # Delete provider (write via cloud)
        await write_db.delete(provider)
        await callback_query.answer(
            f"Provider `{provider.name}` deleted!", show_alert=True
        )
        await show_providers_list(client, callback_query.message, 0)

    elif action == "models":
        # Handle nested actions for models callback
        if len(extra_args) >= 2 and extra_args[0] == "page":
            # Pagination callback: provider/models/{provider_id}/page/{page}
            page = int(extra_args[1])
            await show_provider_models(
                client, callback_query.message, provider.id, provider.name, page
            )
        elif len(extra_args) >= 1 and extra_args[0] == "back":
            # Back from models to provider details
            await provider_handler(client, callback_query)
        elif len(extra_args) >= 1:
            # Model selection callback: provider/models/{provider_id}/{model_name}
            # Currently just show the models list (could be extended to show model details)
            await show_provider_models(
                client, callback_query.message, provider.id, provider.name, 0
            )
        else:
            # Initial models view
            await show_provider_models(
                client, callback_query.message, provider.id, provider.name, 0
            )


async def show_providers_list(client: Client, message: types.Message, page: int = 0):
    """Display providers list with action buttons."""
    from sqlalchemy import select

    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    default_provider = await read_db.get_default_provider()

    if not providers:
        await message.edit_text(
            "No providers yet. Add a provider using:\n"
            "`/add_provider <name> <base_url> <api_key>`"
        )
        return

    # Prepare providers list with (id, name) tuples
    providers_list = [(p.id, p.name) for p in providers]

    # Create action buttons keyboard
    markup = create_provider_actions_keyboard(
        providers=providers_list,
        callback_prefix="provider",
    )

    # Build message with provider names
    provider_info = []
    for provider in providers:
        is_default = default_provider and provider.id == default_provider.id
        status = " ⭐ (Default)" if is_default else ""
        provider_info.append(f"🔹 **{provider.name}**{status}")

    providers_text = "\n".join(provider_info)
    new_text = f"**AI Providers**\n\n{providers_text}\n\nUse the buttons below to manage each provider."

    # Check if message unchanged, skip edit_text call
    if message.text != new_text or str(message.reply_markup) != str(markup):
        await message.edit_text(new_text, reply_markup=markup)


async def show_provider_models(
    client: Client,
    message: types.Message,
    provider_id: int,
    provider_name: str,
    page: int,
):
    """Display models list of a provider with pagination using numbered buttons."""
    from app.ai.base import models as get_models

    all_models = await get_models()

    total_pages = max(1, (len(all_models) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(all_models))
    page_models = all_models[start_idx:end_idx]

    # Create numbered keyboard
    markup = create_models_keyboard(
        models=page_models,
        page=page,
        callback_prefix=f"provider/models/{provider_id}",
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
