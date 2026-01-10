"""Command handlers for AI provider and model management."""

from pyrogram import Client, enums, filters, types
from sqlalchemy import select

from app.ai.base import get_model
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


@Client.on_callback_query(filters.regex(r"noop"))
async def noop_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle noop callbacks (do nothing)"""
    await callback_query.answer()


@Client.on_callback_query(
    filters.regex(r"models/close")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def models_close_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle close for models list"""
    await callback_query.message.delete()
    if callback_query.message.reply_to_message:
        await callback_query.message.reply_to_message.delete()


@Client.on_callback_query(
    filters.regex(r"provider/close")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_close_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle close for providers list"""
    await callback_query.message.delete()
    if callback_query.message.reply_to_message:
        await callback_query.message.reply_to_message.delete()


# Removed provider_number_handler - no longer needed with action buttons


@Client.on_message(
    filters.command("models")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def models_handler(client: Client, message: types.Message, page: int = 0):
    """List available models with pagination"""
    from app.ai.base import models as get_models
    from app.handlers.ai_provider.pagination import create_models_keyboard

    await message.reply_chat_action(enums.ChatAction.TYPING)
    all_models = await get_models()
    current_model = await get_model()

    # Build models list - only add current model to top if it's not empty
    models_list = list(all_models)
    if current_model and current_model in models_list:
        models_list.remove(current_model)
        models_list.insert(0, current_model)
    elif current_model:
        # Current model not in all_models list, add it to top
        models_list.insert(0, current_model)

    total_pages = max(1, (len(models_list) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(models_list))
    page_models = models_list[start_idx:end_idx]

    markup = create_models_keyboard(
        models=page_models,
        page=page,
        callback_prefix="models",
        total_pages=total_pages,
    )

    # Build message with model names
    start_num = page * ITEMS_PER_PAGE + 1
    model_names = []
    for i, model in enumerate(page_models):
        num = start_num + i
        is_selected = model == current_model
        prefix = "✅ " if is_selected else ""
        model_names.append(f"`{num}`. {prefix}`{model}`")

    models_text = "\n".join(model_names)

    await message.reply(
        f"**Models** (Page {page + 1}/{total_pages})\n\n"
        f"{models_text}\n\n"
        f"Tap a number to select model.",
        reply_markup=markup,
        quote=True,
    )


@Client.on_callback_query(
    filters.regex(r"models/page/")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def models_page_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle pagination for models list"""

    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    page = int(parts[-1])

    all_models = await get_models()
    current_model = await get_model()

    # Move current model to top and mark it
    models_list = list(all_models)
    if current_model in models_list:
        models_list.remove(current_model)
    models_list.insert(0, current_model)

    total_pages = max(1, (len(models_list) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(models_list))
    page_models = models_list[start_idx:end_idx]

    markup = create_models_keyboard(
        models=page_models,
        page=page,
        callback_prefix="models",
        total_pages=total_pages,
    )

    # Build message with model names
    start_num = page * ITEMS_PER_PAGE + 1
    model_names = []
    for i, model in enumerate(page_models):
        num = start_num + i
        is_selected = model == current_model
        prefix = "✅ " if is_selected else ""
        model_names.append(f"`{num}`. {prefix}`{model}`")

    models_text = "\n".join(model_names)

    await callback_query.message.edit_text(
        f"**Models** (Page {page + 1}/{total_pages})\n\n"
        f"{models_text}\n\n"
        f"Tap a number to select model.",
        reply_markup=markup,
    )


@Client.on_callback_query(
    filters.regex(r"models/\d+")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def models_number_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle model selection from list via number button"""
    from app.ai.base import models as get_models

    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    
    # Kiểm tra định dạng callback data
    if len(parts) < 2:
        await callback_query.answer("Invalid callback data format!", show_alert=True)
        return
        
    try:
        model_num = int(parts[1])
    except ValueError:
        await callback_query.answer("Invalid model number!", show_alert=True)
        return

    all_models = await get_models()
    current_model = await get_model()

    # Build models list - only add current model to top if it's not empty
    models_list = list(all_models)
    if current_model and current_model in models_list:
        models_list.remove(current_model)
        models_list.insert(0, current_model)
    elif current_model:
        # Current model not in all_models list, add it to top
        models_list.insert(0, current_model)

    if 1 <= model_num <= len(models_list):
        model_id = models_list[model_num - 1]
        # Save to database instead of environment variable
        provider = await read_db.get_default_provider()
        if provider:
            await write_db.set_default_model("chat", provider.name, model_id)
            await callback_query.answer(
                f"Selected model: `{model_id}`", show_alert=True
            )
        else:
            await callback_query.answer("No provider configured!", show_alert=True)
        # Delete the models list message
        await callback_query.message.delete()
    else:
        await callback_query.answer("Invalid model number!", show_alert=True)


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


@Client.on_message(
    filters.command("setmodel")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def set_model_command_handler(client: Client, message: types.Message):
    """Set default model for features (chat, translate)"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    buttons = [
        [
            types.InlineKeyboardButton(
                text="💬 Chat", callback_data="setmodel/feature/chat"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🌐 Translate", callback_data="setmodel/feature/translate"
            )
        ],
    ]
    markup = types.InlineKeyboardMarkup(buttons)

    # Show current models
    chat_model = await read_db.get_default_model("chat")
    translate_model = await read_db.get_default_model("translate")

    current_info = ""
    if chat_model:
        current_info += f"💬 Chat: `{chat_model.provider_name}/{chat_model.model}`\n"
    if translate_model:
        current_info += (
            f"🌐 Translate: `{translate_model.provider_name}/{translate_model.model}`\n"
        )

    if current_info:
        current_info = "**Current models:**\n" + current_info + "\n"

    await message.reply(
        f"{current_info}**Select Feature**\n\nChoose a feature to set default model:",
        reply_markup=markup,
        quote=True,
    )


@Client.on_message(
    filters.command("add_provider")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def add_provider_handler(client: Client, message: types.Message):
    """Add new AI provider from Telegram by OWNER.
    Usage: /add_provider <name> <base_url> <api_key>"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    args = message.text.split()
    if len(args) < 4:
        await message.reply(
            "**Usage:** `/add_provider <name> <base_url> <api_key>`\n\n"
            "Example:\n"
            "`/add_provider oai https://api.openai.com/v1 sk-xxx`\n\n"
            "Then use `/providers` to manage.",
            quote=True,
        )
        return

    name = args[1]
    base_url = args[2]
    api_key = args[3]

    # Check if provider already exists (read from local)
    existing = await read_db.get_provider_by_name(name)
    if existing:
        existing.base_url = base_url
        existing.api_key = api_key
        await write_db.commit()
        await message.reply(f"Provider `{name}` updated!", quote=True)
    else:
        provider = AIProvider(
            name=name,
            base_url=base_url,
            api_key=api_key,
        )
        await write_db.add(provider)
        # If no default provider, set this as default
        if await read_db.get_default_provider() is None:
            await write_db.set_default_provider(provider)
        await message.reply(f"Provider `{name}` added!", quote=True)


@Client.on_message(
    filters.command("providers")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def providers_handler(client: Client, message: types.Message, page: int = 0):
    """List AI providers with pagination"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    default_provider = await read_db.get_default_provider()

    if not providers:
        await message.reply(
            "No providers yet. Add a provider using:\n"
            "`/add_provider <name> <base_url> <api_key>`",
            quote=True,
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

    await message.reply(
        f"**AI Providers** (Page {page + 1}/{total_pages})\n\n"
        f"{providers_text}\n\n"
        f"Tap a number to select provider.",
        reply_markup=markup,
        quote=True,
    )
