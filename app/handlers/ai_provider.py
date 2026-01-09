import os

from ai.base import get_model, models
from database.cloud import cloud_db
from database.local import local_db
from database.models import AIProvider, DefaultModel, TelegramGroup, TelegramUser
from handlers.owner import is_user_owner
from pyrogram import Client, enums, filters, types
from sqlalchemy import select

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


# Paging constants
PROVIDERS_PER_PAGE = 6
MODELS_PER_PAGE = 6


def create_pagination_buttons(page: int, total_pages: int, callback_prefix: str) -> list:
    """Tạo các nút phân trang"""
    buttons = []
    row = []
    
    if page > 0:
        row.append(types.InlineKeyboardButton(text="◀ Prev", callback_data=f"{callback_prefix}/page/{page - 1}"))
    
    row.append(types.InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"{callback_prefix}/page/{page}"))
    
    if page < total_pages - 1:
        row.append(types.InlineKeyboardButton(text="Next ▶", callback_data=f"{callback_prefix}/page/{page + 1}"))
    
    if row:
        buttons.append(row)
    
    return buttons


@Client.on_callback_query(
    filters.regex(r"openai/") & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def select_model_handler(client: Client, callback_query: types.CallbackQuery):
    """Chọn model AI"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    model_id = str(callback_query.data).split("/")[1]
    os.environ["AGENT_MODEL"] = model_id
    await callback_query.answer(f"Selected model: `{model_id}`", show_alert=True)
    await callback_query.message.delete()
    await callback_query.message.reply_to_message.delete()


@Client.on_callback_query(
    filters.regex(r"provider/") & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def provider_handler(client: Client, callback_query: types.CallbackQuery):
    """Xử lý callback quản lý provider"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    _, action, provider_id_str = str(callback_query.data).split("/")
    provider_id = int(provider_id_str)

    # Lấy provider từ database (đọc từ local)
    result = await read_db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalars().first()

    if not provider:
        await callback_query.answer("Provider not found!", show_alert=True)
        return

    if action == "select":
        # Chọn provider làm mặc định (ghi qua cloud)
        await write_db.set_default_provider(provider)
        await callback_query.answer(
            f"Provider `{provider.name}` is now default!", show_alert=True
        )
        # Refresh message
        await providers_refresh(client, callback_query.message)

    elif action == "edit":
        # Hiển thị menu với các tùy chọn: Select, Edit, Models, Delete
        buttons = [
            [
                types.InlineKeyboardButton(
                    text="Select",
                    callback_data=f"provider/select/{provider.id}",
                ),
                types.InlineKeyboardButton(
                    text="Edit",
                    callback_data=f"provider/edit_update/{provider.id}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Models",
                    callback_data=f"provider/models/{provider.id}",
                ),
                types.InlineKeyboardButton(
                    text="Delete",
                    callback_data=f"provider/delete/{provider.id}",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="providers/list",
                ),
            ],
        ]
        markup = types.InlineKeyboardMarkup(buttons)
        default_provider = await read_db.get_default_provider()
        default_tag = " ⭐ (Default)" if default_provider and provider.id == default_provider.id else ""
        await callback_query.message.edit_text(
            f"**Provider: {provider.name}**{default_tag}\n\n"
            f"URL: `{provider.base_url}`\n"
            f"API Key: `{provider.api_key[:10]}...`",
            reply_markup=markup,
        )

    elif action == "delete":
        # Xóa provider (ghi qua cloud)
        await write_db.delete(provider)
        await callback_query.answer(
            f"Provider `{provider.name}` deleted!", show_alert=True
        )
        await providers_refresh(client, callback_query.message)

    elif action == "models":
        # Hiển thị models của provider
        from ai.base import models as get_models

        try:
            all_models = get_models()
            buttons = [
                types.InlineKeyboardButton(
                    text=model,
                    callback_data=f"openai/{model}",
                )
                for model in all_models
            ]
            buttons.append(
                types.InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data=f"provider/edit/{provider.id}",
                )
            )
            markup = types.InlineKeyboardMarkup(
                [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
            )
            await callback_query.message.edit_text(
                f"**Models for {provider.name}**",
                reply_markup=markup,
            )
        except Exception as e:
            await callback_query.answer(f"Error: {str(e)}", show_alert=True)

    elif action == "list":
        # Refresh danh sách providers
        await providers_refresh(client, callback_query.message)


@Client.on_callback_query(
    filters.regex(r"setmodel/") & filters.create(lambda _, __, cq: is_user_owner(cq.from_user.id))  # type: ignore
)
async def set_model_handler(client: Client, callback_query: types.CallbackQuery):
    """Xử lý callback cho lệnh /set_model"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    parts = str(callback_query.data).split("/")
    
    if len(parts) < 2:
        return
    
    action = parts[1]
    
    if action == "feature":
        # Chọn feature (chat hoặc translate)
        feature = parts[2] if len(parts) > 2 else None
        if feature:
            # Hiển thị danh sách provider cho feature này
            await show_providers_for_feature(client, callback_query.message, feature, 0)
        else:
            # Hiển thị danh sách feature
            buttons = [
                [types.InlineKeyboardButton(text="💬 Chat", callback_data="setmodel/feature/chat")],
                [types.InlineKeyboardButton(text="🌐 Translate", callback_data="setmodel/feature/translate")],
            ]
            markup = types.InlineKeyboardMarkup(buttons)
            await callback_query.message.edit_text(
                "**Chọn Feature**\n\nChọn feature để đặt model mặc định:",
                reply_markup=markup,
            )
    
    elif action == "provider":
        # Chọn provider cho feature
        feature = parts[2]
        provider_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 0
        
        # Hiển thị models của provider
        await show_models_for_provider(client, callback_query.message, feature, provider_id, 0)
    
    elif action == "model":
        # Chọn model cho feature và provider
        feature = parts[2]
        provider_id = int(parts[3])
        model_name = "/".join(parts[4:])  # Model name có thể chứa /
        
        # Lưu vào DefaultModel (ghi qua cloud, sẽ mirror sang local)
        provider = await read_db.get(AIProvider, id=provider_id)
        provider = provider.scalars().first()
        if provider:
            await write_db.set_default_model(feature, provider.name, model_name)
            await callback_query.answer(f"Đã đặt `{model_name}` làm model mặc định cho {feature}!", show_alert=True)
        
        # Quay lại danh sách providers
        await show_providers_for_feature(client, callback_query.message, feature, 0)
    
    elif action == "page":
        # Phân trang
        callback_type = parts[2]  # feature, provider, hoặc model
        page = int(parts[3])
        
        if callback_type == "feature":
            # Đang ở trang chọn feature
            await show_providers_for_feature(client, callback_query.message, parts[4], page)
        elif callback_type == "provider":
            # Đang ở trang chọn provider
            feature = parts[4]
            provider_id = int(parts[5])
            await show_models_for_provider(client, callback_query.message, feature, provider_id, page)


async def show_providers_for_feature(client: Client, message: types.Message, feature: str, page: int):
    """Hiển thị danh sách providers cho một feature với phân trang"""
    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    
    total_pages = max(1, (len(providers) + PROVIDERS_PER_PAGE - 1) // PROVIDERS_PER_PAGE)
    start_idx = page * PROVIDERS_PER_PAGE
    end_idx = min(start_idx + PROVIDERS_PER_PAGE, len(providers))
    page_providers = providers[start_idx:end_idx]
    
    buttons = []
    for provider in page_providers:
        # Kiểm tra provider này có được chọn cho feature không
        default_model = await read_db.get_default_model(feature)
        is_selected = default_model and default_model.provider_name == provider.name
        prefix = "✅ " if is_selected else ""
        buttons.append([
            types.InlineKeyboardButton(
                text=f"{prefix}{provider.name}",
                callback_data=f"setmodel/provider/{feature}/{provider.id}",
            )
        ])
    
    # Thêm nút phân trang
    pagination_buttons = create_pagination_buttons(page, total_pages, f"setmodel/page/feature/{feature}")
    if pagination_buttons:
        buttons.extend(pagination_buttons)
    
    # Thêm nút quay lại
    buttons.append([types.InlineKeyboardButton(text="⬅️ Back", callback_data="setmodel/feature")])
    
    markup = types.InlineKeyboardMarkup(buttons)
    feature_name = "Chat" if feature == "chat" else "Translate"
    await message.edit_text(
        f"**Chọn Provider cho {feature_name}**\n\nTrang {page + 1}/{total_pages}",
        reply_markup=markup,
    )


async def show_models_for_provider(client: Client, message: types.Message, feature: str, provider_id: int, page: int):
    """Hiển thị danh sách models của một provider với phân trang"""
    provider = await read_db.get(AIProvider, id=provider_id)
    provider = provider.scalars().first()
    
    if not provider:
        await message.edit_text("Provider không tồn tại!")
        return
    
    from ai.base import models as get_models
    all_models = get_models()
    
    total_pages = max(1, (len(all_models) + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE)
    start_idx = page * MODELS_PER_PAGE
    end_idx = min(start_idx + MODELS_PER_PAGE, len(all_models))
    page_models = all_models[start_idx:end_idx]
    
    # Lấy default model hiện tại
    default_model = await read_db.get_default_model(feature)
    
    buttons = []
    for model in page_models:
        is_selected = default_model and default_model.model == model
        prefix = "✅ " if is_selected else ""
        buttons.append([
            types.InlineKeyboardButton(
                text=f"{prefix}{model}",
                callback_data=f"setmodel/model/{feature}/{provider_id}/{model}",
            )
        ])
    
    # Thêm nút phân trang
    pagination_buttons = create_pagination_buttons(page, total_pages, f"setmodel/page/provider/{feature}/{provider_id}")
    if pagination_buttons:
        buttons.extend(pagination_buttons)
    
    # Thêm nút quay lại
    buttons.append([types.InlineKeyboardButton(text="⬅️ Back", callback_data=f"setmodel/feature/{feature}")])
    
    markup = types.InlineKeyboardMarkup(buttons)
    feature_name = "Chat" if feature == "chat" else "Translate"
    await message.edit_text(
        f"**Chọn Model cho {feature_name} ({provider.name})**\n\nTrang {page + 1}/{total_pages}",
        reply_markup=markup,
    )


async def providers_refresh(client: Client, message: types.Message):
    """Refresh message hiển thị danh sách providers (đọc từ local)"""
    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    default_provider = await read_db.get_default_provider()

    if not providers:
        await message.edit_text(
            "Chưa có provider nào. Thêm provider bằng:\n"
            "`/add_provider <name> <base_url> <api_key>`"
        )
        return

    buttons = []
    for provider in providers:
        prefix = "⭐ " if default_provider and provider.id == default_provider.id else "  "
        buttons.append(
            [
                types.InlineKeyboardButton(
                    text=f"{prefix}{provider.name}",
                    callback_data=f"provider/edit/{provider.id}",
                ),
                types.InlineKeyboardButton(
                    text="Select",
                    callback_data=f"provider/select/{provider.id}",
                ),
            ]
        )

    markup = types.InlineKeyboardMarkup(buttons)
    await message.edit_text(
        "**AI Providers**\n\nNhấn vào tên provider để chỉnh sửa, 'Select' để chọn làm mặc định.",
        reply_markup=markup,
    )


@Client.on_message(
    filters.command("models") & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def models_handler(client: Client, message: types.Message):
    """Liệt kê các model có sẵn"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    all_models = models()
    current_model = get_model()
    markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    text=model,
                    callback_data=f"openai/{model}",
                )
            ]
            for model in all_models
        ]
    )
    await message.reply(
        f"Current model: `{current_model}`", reply_markup=markup, quote=True
    )


@Client.on_message(
    filters.command("setmodel") & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def set_model_command_handler(client: Client, message: types.Message):
    """Đặt model mặc định cho các feature (chat, translate)"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    
    buttons = [
        [types.InlineKeyboardButton(text="💬 Chat", callback_data="setmodel/feature/chat")],
        [types.InlineKeyboardButton(text="🌐 Translate", callback_data="setmodel/feature/translate")],
    ]
    markup = types.InlineKeyboardMarkup(buttons)
    
    # Hiển thị model hiện tại
    chat_model = await read_db.get_default_model("chat")
    translate_model = await read_db.get_default_model("translate")
    
    current_info = ""
    if chat_model:
        current_info += f"💬 Chat: `{chat_model.provider_name}/{chat_model.model}`\n"
    if translate_model:
        current_info += f"🌐 Translate: `{translate_model.provider_name}/{translate_model.model}`\n"
    
    if current_info:
        current_info = "**Model hiện tại:**\n" + current_info + "\n"
    
    await message.reply(
        f"{current_info}**Chọn Feature**\n\nChọn feature để đặt model mặc định:",
        reply_markup=markup,
        quote=True,
    )


@Client.on_message(
    filters.command("add_provider") & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def add_provider_handler(client: Client, message: types.Message):
    """Thêm AI provider mới từ Telegram bởi OWNER.
    Usage: /add_provider <name> <base_url> <api_key>"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    args = message.text.split()
    if len(args) < 4:
        await message.reply(
            "**Usage:** `/add_provider <name> <base_url> <api_key>`\n\n"
            "Example:\n"
            "`/add_provider oai https://api.openai.com/v1 sk-xxx`\n\n"
            "Sau đó dùng `/providers` để quản lý.",
            quote=True,
        )
        return

    name = args[1]
    base_url = args[2]
    api_key = args[3]

    # Kiểm tra provider đã tồn tại chưa (đọc từ local)
    existing = await read_db.get_provider_by_name(name)
    if existing:
        existing.base_url = base_url
        existing.api_key = api_key
        await write_db.commit()
        await message.reply(f"Provider `{name}` đã được cập nhật!", quote=True)
    else:
        provider = AIProvider(
            name=name,
            base_url=base_url,
            api_key=api_key,
        )
        await write_db.add(provider)
        # Nếu chưa có provider nào, đặt làm mặc định
        if await read_db.get_default_provider() is None:
            await write_db.set_default_provider(provider)
        await message.reply(f"Provider `{name}` đã được thêm!", quote=True)


@Client.on_message(
    filters.command("providers") & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def providers_handler(client: Client, message: types.Message):
    """Liệt kê và quản lý AI providers (đọc từ local)"""
    await message.reply_chat_action(enums.ChatAction.TYPING)

    result = await read_db.execute(select(AIProvider))
    providers = result.scalars().all()
    default_provider = await read_db.get_default_provider()

    if not providers:
        await message.reply(
            "Chưa có provider nào. Thêm provider bằng:\n"
            "`/add_provider <name> <base_url> <api_key>`",
            quote=True,
        )
        return

    buttons = []
    for provider in providers:
        prefix = "⭐ " if default_provider and provider.id == default_provider.id else "  "
        buttons.append(
            [
                types.InlineKeyboardButton(
                    text=f"{prefix}{provider.name}",
                    callback_data=f"provider/edit/{provider.id}",
                ),
                types.InlineKeyboardButton(
                    text="Select",
                    callback_data=f"provider/select/{provider.id}",
                ),
            ]
        )

    markup = types.InlineKeyboardMarkup(buttons)
    await message.reply(
        "**AI Providers**\n\nNhấn vào tên provider để chỉnh sửa, 'Select' để chọn làm mặc định.",
        reply_markup=markup,
        quote=True,
    )
