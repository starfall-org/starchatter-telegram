from app.handlers.admin.owner import is_user_owner
from app.handlers.ai_provider.pagination import ITEMS_PER_PAGE, create_models_keyboard
from pyrogram import Client, enums, filters, types

from app.ai.base import get_model
from app.ai.base import models as get_models


@Client.on_message(
    filters.command("models")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def models_handler(client: Client, message: types.Message, page: int = 0):
    """List available models with pagination"""

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
