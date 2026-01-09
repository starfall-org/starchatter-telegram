import asyncio

from ai.text import localize
from database.cloud import cloud_db
from database.local import local_db
from database.models import TelegramGroup, TelegramUser
from pyrogram import Client, enums, filters, types
from utils import is_chat_admin, is_chat_owner, is_owner

db = cloud_db

basic_buttons = [
    types.InlineKeyboardButton(text="Channel", url="https://t.me/starfall_org"),
    types.InlineKeyboardButton(text="Group", url="https://t.me/starfall_community"),
    types.InlineKeyboardButton(text="Discord", url="https://discord.gg/9WF54BSc4s"),
]


def _get_state_key(chat_id: int, state_type: str) -> str:
    """Tạo key cho state lưu trong local database"""
    return f"group_{chat_id}_{state_type}"


async def _get_group_state(chat_id: int) -> dict:
    """Lấy state của group từ local database"""
    chatbot_disabled = await local_db.get_state(_get_state_key(chat_id, "chatbot_disabled"))
    anti_spam_disabled = await local_db.get_state(_get_state_key(chat_id, "anti_spam_disabled"))
    return {
        "chatbot_disabled": chatbot_disabled == "true",
        "anti_spam_disabled": anti_spam_disabled == "true",
    }


async def _set_group_state(chat_id: int, chatbot_disabled: bool, anti_spam_disabled: bool):
    """Lưu state của group vào local database"""
    await local_db.set_state(_get_state_key(chat_id, "chatbot_disabled"), "true" if chatbot_disabled else "false")
    await local_db.set_state(_get_state_key(chat_id, "anti_spam_disabled"), "true" if anti_spam_disabled else "false")


@Client.on_message(filters.command("menu") & filters.group)  # type: ignore
async def group_menu(client: Client, message: types.Message):
    """Hiển thị menu quản trị nhóm"""
    await message.reply_chat_action(enums.ChatAction.TYPING)
    chat_id = message.chat.id
    
    # Lấy state từ local database
    state = await _get_group_state(chat_id)
    
    # Kiểm tra quyền admin
    if not (
        await is_chat_owner(message.from_user, message.chat)
        or await is_chat_admin(message.from_user, message.chat)
        or await is_owner(message.from_user)
    ):
        admin_text = await localize(
            "You must be an admin to access the menu.", user_id=message.from_user.id
        )
        await message.reply(admin_text)
        return

    keyboard_markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    text=("Disable" if state["chatbot_disabled"] else "Enable")
                    + " Chatbot",
                    callback_data="menu/chatbot",
                ),
                types.InlineKeyboardButton(
                    text=("Disable" if state["anti_spam_disabled"] else "Enable")
                    + " Anti-Spam",
                    callback_data="menu/anti_spam",
                ),
            ],
            [types.InlineKeyboardButton(text="Goodbye", callback_data="menu/goodbye")],
            [button for button in basic_buttons],
        ]
    )

    menu_text = await localize("Group Admin Menu:", user_id=message.from_user.id)
    await message.reply(menu_text, reply_markup=keyboard_markup)


@Client.on_callback_query(
    filters.regex(r"menu/")  # type: ignore
)
async def group_admin_menu_handler(client: Client, callback_query: types.CallbackQuery):
    """Xử lý callback từ menu quản trị nhóm"""
    await callback_query.message.reply_chat_action(enums.ChatAction.TYPING)
    action = str(callback_query.data)
    chat_id = callback_query.message.chat.id
    
    # Kiểm tra quyền admin
    if not (
        await is_chat_owner(callback_query.from_user, callback_query.message.chat)
        or await is_chat_admin(callback_query.from_user, callback_query.message.chat)
        or await is_owner(callback_query.from_user)
    ):
        admin_text = await localize(
            "You must be an admin to perform this action.",
            user_id=callback_query.from_user.id
        )
        await callback_query.answer(admin_text)
        return
    
    # Lấy state hiện tại
    state = await _get_group_state(chat_id)
    
    if action == "menu/chatbot":
        # Toggle chatbot state
        new_chatbot_disabled = not state["chatbot_disabled"]
        await _set_group_state(chat_id, new_chatbot_disabled, state["anti_spam_disabled"])
        
        chatbot_status = await localize(
            "Chatbot disabled for this group." if new_chatbot_disabled else "Chatbot enabled for this group.",
            user_id=callback_query.from_user.id
        )
        await callback_query.answer(chatbot_status)
        await callback_query.message.edit_text(chatbot_status)
        
    elif action == "menu/anti_spam":
        # Toggle anti-spam state
        new_anti_spam_disabled = not state["anti_spam_disabled"]
        await _set_group_state(chat_id, state["chatbot_disabled"], new_anti_spam_disabled)
        
        antispam_status = await localize(
            "Anti-Spam disabled for this group." if new_anti_spam_disabled else "Anti-Spam enabled for this group.",
            user_id=callback_query.from_user.id
        )
        await callback_query.answer(antispam_status)
        await callback_query.message.edit_text(antispam_status)
        
    elif action == "menu/goodbye":
        goodbye_text = await localize(
            "Goodbye! 👋",
            user_id=callback_query.from_user.id
        )
        await callback_query.answer(goodbye_text)
        await callback_query.message.edit_text(goodbye_text)
        await asyncio.sleep(3)
        await client.leave_chat(chat_id)


async def is_chatbot_enabled(chat_id: int) -> bool:
    """Kiểm tra chatbot có được bật không"""
    state = await _get_group_state(chat_id)
    return not state["chatbot_disabled"]


async def is_anti_spam_enabled(chat_id: int) -> bool:
    """Kiểm tra anti-spam có được bật không"""
    state = await _get_group_state(chat_id)
    return not state["anti_spam_disabled"]
