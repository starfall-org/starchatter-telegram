from app.handlers.owner import is_user_owner
from app.handlers.pagination import (
    ITEMS_PER_PAGE,
    create_models_keyboard,
)
from pyrogram import Client, enums, filters, types

from app.ai.base import get_model
from app.ai.base import models as get_models
from app.database.cloud import cloud_db
from app.database.local import local_db

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


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
        await callback_query.answer("Internal error!", show_alert=True)
        return

    try:
        model_num = int(parts[1])
    except ValueError:
        await callback_query.answer("Internal error!", show_alert=True)
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
        await callback_query.answer("Internal error!", show_alert=True)
