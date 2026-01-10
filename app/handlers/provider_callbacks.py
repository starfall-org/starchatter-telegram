"""Provider callback handler for AI provider management."""

from pyrogram import Client, enums, filters, types
from sqlalchemy import select

from app.ai.base import get_provider_models
from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider
from app.handlers.admin.owner import is_user_owner
from app.handlers.ai_provider.pagination import (
    ITEMS_PER_PAGE,
    create_models_keyboard,
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

    # Handle variable number of parts
    action = parts[1] if len(parts) > 1 else ""

    # Handle pagination: provider/page/{page}
    if action == "page" and len(parts) > 2:
        page = int(parts[2])
        await show_providers_list(
            client, callback_query.message, page, force_cloud=False
        )
        await callback_query.answer()
        return

    # Handle back from pagination: provider/back
    if action == "back":
        await show_providers_list(client, callback_query.message, 0, force_cloud=False)
        await callback_query.answer()
        return

    # Handle close: provider/close
    if action == "close":
        await callback_query.message.delete()
        if callback_query.message.reply_to_message:
            await callback_query.message.reply_to_message.delete()
        await callback_query.answer()
        return

    # Handle number selection: provider/{number}
    if action.isdigit():
        provider_num = int(action)
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
        return

    # Handle provider_id based actions
    provider_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    # Extract additional args if present (for models/{provider_id}/{model} or models_page/{provider_id}/{page})
    extra_args = parts[3:] if len(parts) > 3 else []

    if provider_id is None:
        await callback_query.answer("Invalid callback!", show_alert=True)
        return

    # Get provider from database (read from local)

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
        # Refresh message - go back to list
        # Use cloud_db to get the latest default provider to ensure consistency
        await show_providers_list(client, callback_query.message, 0, force_cloud=True)

    elif action == "edit":
        # Show edit form for provider details
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="provider/back",
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
        await show_providers_list(client, callback_query.message, 0, force_cloud=False)

    elif action == "models":
        # Handle nested actions for models callback
        if len(extra_args) >= 2 and extra_args[0] == "page":
            # Pagination callback: provider/models/{provider_id}/page/{page}
            page = int(extra_args[1])
            await show_provider_models(
                client, callback_query.message, provider.id, provider.name, page
            )
        elif len(extra_args) >= 1 and extra_args[0] == "back":
            # Back from models to provider actions
            await show_provider_actions(
                client, callback_query.message, provider, force_cloud=False
            )
        elif len(extra_args) >= 1:
            # Model selection callback: provider/models/{provider_id}/{model_number}
            if extra_args[0].isdigit():
                # Handle model selection by number
                model_number = int(extra_args[0])

                all_models = await get_provider_models(provider=provider)

                # Check if models list is empty
                if not all_models:
                    await callback_query.answer("No models available!", show_alert=True)
                    return

                # Validate model number (1-based indexing)
                if 1 <= model_number <= len(all_models):
                    # Convert from 1-based to 0-based indexing
                    actual_model_index = model_number - 1
                    selected_model = all_models[actual_model_index]
                    # Save selected model to database
                    await write_db.set_default_model(
                        "chat", provider.name, selected_model
                    )
                    await callback_query.answer(
                        f"Selected model: `{selected_model}`", show_alert=True
                    )
                    # Refresh the models list (stay on current page if possible)
                    # Try to extract page from callback query message text
                    page = 0
                    if callback_query.message.text:
                        import re

                        page_match = re.search(
                            r"\(Page (\d+)/(\d+)\)", callback_query.message.text
                        )
                        if page_match:
                            page = (
                                int(page_match.group(1)) - 1
                            )  # Convert to 0-based index
                    await show_provider_models(
                        client, callback_query.message, provider.id, provider.name, page
                    )
                else:
                    await callback_query.answer(
                        "Invalid model number!", show_alert=True
                    )
            else:
                await show_provider_models(
                    client, callback_query.message, provider.id, provider.name, 0
                )
        else:
            # Initial models view
            await show_provider_models(
                client, callback_query.message, provider.id, provider.name, 0
            )

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
                callback_data=f"provider/models/{provider.id}",
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
                    callback_data=f"provider/models/{provider_id}/back",
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


@Client.on_callback_query(
    filters.regex(r"provider/close")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_close_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle close for providers list"""
    await callback_query.message.delete()
    if callback_query.message.reply_to_message:
        await callback_query.message.reply_to_message.delete()


@Client.on_callback_query(
    filters.regex(r"provider/page/")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def providers_page_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle pagination for providers list"""
    from app.handlers.ai_provider.provider_callbacks import show_providers_list

    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    page = int(parts[-1])

    await show_providers_list(client, callback_query.message, page)
