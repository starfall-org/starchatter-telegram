from pyrogram import Client, filters, types

from database.client import Database

db = Database()


@Client.on_callback_query(filters.regex(r"^\d+$"))
async def callback_handler(client: Client, callback_query: types.CallbackQuery):
    provider_id = int(callback_query.data)
    await db.edit_llm_config(provider_id=provider_id)
    await callback_query.answer("Provider set successfully!")
