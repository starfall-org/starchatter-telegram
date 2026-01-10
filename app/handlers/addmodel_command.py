from pyrogram import Client, filters, types
from app.handlers.owner import is_user_owner
from app.database.local import local_db
from app.database.cloud import cloud_db


@Client.on_message(
    filters.command("addmodel")
    & filters.create(lambda _, __, m: is_user_owner(m.from_user.id))  # type: ignore
)
async def addmodel_handler(client: Client, message: types.Message):
    """Add a model to AIProvider.models list"""
    # Check if there's a model name provided
    if len(message.command) < 2:
        await message.reply(
            "Please provide a model name to add. Usage: /addmodel model_name"
        )
        return

    model_name = message.command[1]

    # Get default provider
    provider = await local_db.get_default_provider()
    provider_cloud = await cloud_db.get_default_provider()
    if not provider:
        await message.reply(
            "No default provider configured. Please set a default provider first."
        )
        return

    # Add model to provider's models list
    if model_name not in provider.models:
        provider.models.append(model_name)
        provider_cloud.models.append(model_name)
        await local_db.commit()
        await cloud_db.commit()
        await message.reply(
            f"Model '{model_name}' added successfully to {provider.name}'s models list."
        )
    else:
        await message.reply(
            f"Model '{model_name}' already exists in {provider.name}'s models list."
        )
