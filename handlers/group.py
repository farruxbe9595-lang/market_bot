from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from config import MARKET_GROUP_ID, DISCUSSION_TOPIC_ID, BOT_USERNAME
from storage import ADD_PRODUCT_FLOW
from utils import is_admin

router = Router()

def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]]
    )

@router.message(Command("add_product"))
async def add_product_start(message: Message, bot):
    if message.chat.id != MARKET_GROUP_ID:
        return
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    if message.message_thread_id is None:
        await message.answer("❗ Faqat topic ichida ishlaydi")
        return

    ADD_PRODUCT_FLOW[message.from_user.id] = {
        "step": "photo",
        "topic_id": message.message_thread_id
    }

    await message.answer("🖼 Rasm yuboring:", reply_markup=admin_cancel_kb())

@router.message(F.photo)
async def add_product_photo(message: Message):
    data = ADD_PRODUCT_FLOW.get(message.from_user.id)
    if not data or data["step"] != "photo":
        return

    data["photo"] = message.photo[-1].file_id
    data["step"] = "text"

    await message.answer("📝 Tavsif yuboring:", reply_markup=admin_cancel_kb())

@router.message(F.text)
async def add_product_text_or_id(message: Message, bot):
    data = ADD_PRODUCT_FLOW.get(message.from_user.id)
    if not data:
        return

    if data["step"] == "text":
        data["text"] = message.text
        data["step"] = "id"
        await message.answer("🆔 Mahsulot ID yozing:", reply_markup=admin_cancel_kb())
        return

    if data["step"] == "id":
        product_id = message.text.strip()

        await bot.send_photo(
            chat_id=MARKET_GROUP_ID,
            message_thread_id=data["topic_id"],
            photo=data["photo"],
            caption=f"🆔 ID: {product_id}\n\n{data['text']}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🛒 Buyurtma berish",
                        url=f"https://t.me/{BOT_USERNAME}?start=order_{product_id}"
                    )
                ]]
            )
        )

        ADD_PRODUCT_FLOW.pop(message.from_user.id, None)

@router.callback_query(F.data == "cancel_add")
async def cancel_add(call: CallbackQuery):
    ADD_PRODUCT_FLOW.pop(call.from_user.id, None)
    await call.message.delete()
    await call.answer("Bekor qilindi")

@router.message(F.chat.id == MARKET_GROUP_ID, F.text)
async def topic_guard(message: Message, bot):
    if message.message_thread_id == DISCUSSION_TOPIC_ID:
        return
    if await is_admin(bot, message.chat.id, message.from_user.id):
        return
    if message.text.startswith("/"):
        return
    await message.delete()
