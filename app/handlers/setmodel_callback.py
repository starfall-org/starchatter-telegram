"""Set model handler for AI provider management."""

from pyrogram import Client, enums, filters, types

from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider
from app.handlers.ai_provider.pagination import (
    ITEMS_PER_PAGE,
    create_models_keyboard,
    create_providers_keyboard,
)
from app.handlers.admin.owner import is_user_owner

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


@Client.on_callback_query(
    filters.regex(r"setmodel/")
    & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def set_model_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle callback for /set_model command"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")

    if len(parts) < 2:
        return

    action = parts[1]

    if action == "feature":
        # Select feature (chat or translate)
        feature = parts[2] if len(parts) > 2 else None
        if feature:
            # Show providers list for this feature
            await show_providers_for_feature(client, callback_query.message, feature, 0)
        else:
            # Show features list
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
            await callback_query.message.edit_text(
                "**Select Feature**\n\nChoose a feature to set default model:",
                reply_markup=markup,
            )

    elif action == "provider":
        # Select provider for feature
        feature = parts[2]
        if len(parts) > 3 and parts[3] == "back":
            # Back to features list
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
            await callback_query.message.edit_text(
                "**Select Feature**\n\nChoose a feature to set default model:",
                reply_markup=markup,
            )
            return

        if len(parts) > 3 and parts[3] == "close":
            # Close and delete messages
            await callback_query.message.delete()
            if callback_query.message.reply_to_message:
                await callback_query.message.reply_to_message.delete()
            return

        provider_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 0

        # Show models of provider
        await show_models_for_provider(
            client, callback_query.message, feature, provider_id, 0
        )

    elif action == "model":
        # Select model for feature and provider
        feature = parts[2]
        provider_id = int(parts[3])
        model_name = "/".join(parts[4:])  # Model name may contain /

        if model_name == "back":
            # Back to providers list
            await show_providers_for_feature(client, callback_query.message, feature, 0)
            return

        if model_name == "close":
            # Close and delete messages
            await callback_query.message.delete()
            if callback_query.message.reply_to_message:
                await callback_query.message.reply_to_message.delete()
            return

        # Save to DefaultModel (write via cloud, will mirror to local)
        provider = await read_db.get(AIProvider, id=provider_id)
        if provider:
            await write_db.set_default_model(feature, provider.name, model_name)
            await callback_query.answer(
                f"Set `{model_name}` as default model for {feature}!",
                show_alert=True,
            )

        # Back to providers list
        await show_providers_for_feature(client, callback_query.message, feature, 0)

    elif action == "page":
        # Pagination
        callback_type = parts[2]  # feature, provider, or model
        page = int(parts[3])

        if callback_type == "feature":
            # On feature selection page
            await show_providers_for_feature(
                client, callback_query.message, parts[4], page
            )
        elif callback_type == "provider":
            # On provider selection page
            feature = parts[4]
            provider_id = int(parts[5])
            await show_models_for_provider(
                client, callback_query.message, feature, provider_id, page
            )


async def show_providers_for_feature(
    client: Client, message: types.Message, feature: str, page: int
):
    """Display providers list for a feature with numbered pagination"""
    from sqlalchemy import select

    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()

    total_pages = max(1, (len(providers) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(providers))
    page_providers = providers[start_idx:end_idx]

    # Prepare providers list with (id, name) tuples
    providers_list = [(p.id, p.name) for p in page_providers]

    # Create numbered keyboard
    markup = create_providers_keyboard(
        providers=providers_list,
        page=page,
        callback_prefix=f"setmodel/provider/{feature}",
        total_pages=total_pages,
    )

    # Get current default model for this feature
    default_model = await read_db.get_default_model(feature)

    # Build message with provider names
    start_num = page * ITEMS_PER_PAGE + 1
    provider_names = []
    for i, provider in enumerate(page_providers):
        num = start_num + i
        is_selected = default_model and default_model.provider_name == provider.name
        prefix = "✅ " if is_selected else ""
        provider_names.append(f"`{num}`. {prefix}{provider.name}")

    providers_text = "\n".join(provider_names)
    feature_name = "Chat" if feature == "chat" else "Translate"

    await message.edit_text(
        f"**Select Provider for {feature_name}** (Page {page + 1}/{total_pages})\n\n"
        f"{providers_text}\n\n"
        f"Tap a number to select provider.",
        reply_markup=markup,
    )


async def show_models_for_provider(
    client: Client, message: types.Message, feature: str, provider_id: int, page: int
):
    """Display models list of a provider with numbered pagination"""
    from app.ai.base import models as get_models
    from sqlalchemy import select

    provider = await read_db.get(AIProvider, id=provider_id)

    if not provider:
        await message.edit_text("Provider does not exist!")
        return

    all_models = await get_models()

    total_pages = max(1, (len(all_models) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(all_models))
    page_models = all_models[start_idx:end_idx]

    # Get current default model
    default_model = await read_db.get_default_model(feature)

    # Create numbered keyboard
    markup = create_models_keyboard(
        models=page_models,
        page=page,
        callback_prefix=f"setmodel/model/{feature}/{provider_id}",
        total_pages=total_pages,
    )

    # Build message with model names
    start_num = page * ITEMS_PER_PAGE + 1
    model_names = []
    for i, model in enumerate(page_models):
        num = start_num + i
        is_selected = default_model and default_model.model == model
        prefix = "✅ " if is_selected else ""
        model_names.append(f"`{num}`. {prefix}`{model}`")

    models_text = "\n".join(model_names)
    feature_name = "Chat" if feature == "chat" else "Translate"

    await message.edit_text(
        f"**Select Model for {feature_name} ({provider.name})** (Page {page + 1}/{total_pages})\n\n"
        f"{models_text}\n\n"
        f"Tap a number to select model.",
        reply_markup=markup,
    )
