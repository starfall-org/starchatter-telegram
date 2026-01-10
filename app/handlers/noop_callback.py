from pyrogram import Client, filters, types


@Client.on_callback_query(filters.regex(r"noop"))
async def noop_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle noop callbacks (do nothing)"""
    await callback_query.answer()
