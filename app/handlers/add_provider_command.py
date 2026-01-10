"""Command handlers for AI provider and model management."""

from app.handlers.owner import is_user_owner
from pyrogram import Client, enums, filters, types

from app.database.cloud import cloud_db
from app.database.local import local_db
from app.database.models import AIProvider

# Write to cloud (mirrors to local), read from local (faster)
write_db = cloud_db
read_db = local_db


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
