from database.client import Database
from database.models import Channel, LLMProvider, User
from pyrogram import Client, enums, filters, types

db = Database()


@Client.on_message(filters.command("start"))
async def start(client: Client, message: types.Message):
    await message.reply("Welcome to StarChatter. How can I help you?")


@Client.on_message(filters.command("edit_config"))
async def edit_config(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    model = (await message.ask("Enter default model name")).text
    instructions = (await message.ask("Enter default instructions")).text
    await db.edit_llm_config(
        model,
        instructions,
    )
    await message.reply("Config updated successfully!")


@Client.on_message(filters.command("set_provider"))
async def set_provider(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    provider_id = (await message.ask("Enter provider ID")).text
    await db.edit_llm_config(provider_id=int(provider_id))
    await message.reply("Provider set successfully!")


@Client.on_message(filters.command("get_config"))
async def get_config(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    llm_config = await db.get_llm_config()
    await message.reply(
        f"Model: {llm_config.model}\nInstructions: {llm_config.instructions}\nProvider: {llm_config.provider.name}"
    )


@Client.on_message(filters.command("add_provider"))
async def add_provider(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    name = (await message.ask("Enter provider name")).text
    api_key = (await message.ask("Enter provider API key")).text
    base_url = (await message.ask("Enter provider base URL")).text
    provider = LLMProvider(name=name, api_key=api_key, base_url=base_url)
    await db.add_provider(provider)
    await message.reply("Provider added successfully!")


@Client.on_message(filters.command("get_providers"))
async def get_providers(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    providers = await db.get_providers()
    await message.reply(
        "\n".join([f"{provider.name} (`{provider.id}`)" for provider in providers])
    )


@Client.on_message(filters.command("add_channel"))
async def add_channel(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    name = (await message.ask("Enter channel name")).text
    channel_id = (await message.ask("Enter channel ID")).text
    channel = Channel(name=name, channel_id=channel_id)
    if user := await db.get_user(message.from_user.id):
        user.channels.append(channel)
        await db.update_user(user)

    else:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.first_name,
            channels=[channel],
        )
        await db.add_user(user)

    await message.reply("Channel added successfully!")


@Client.on_message(filters.command("get_channel"))
async def get_channel(client: Client, message: types.Message):
    await message.reply_chat_action(enums.ChatAction.TYPING)
    if user := await db.get_user(message.from_user.id):
        await message.reply(
            "\n".join([f"{channel.title}" for channel in user.channels])
        )
    else:
        await message.reply("You have no channels")
