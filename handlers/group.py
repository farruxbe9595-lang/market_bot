from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import MARKET_GROUP_ID, BOT_USERNAME
from storage import add_product_flow

router = Router()


def register_group(dp, bot: Bot, bot_username: str):
    dp.include_router(router)


@router.message(Command("add_product"))
async def add_product_start(message: Message, bot: Bot):
    if message.chat.id != MARKET_GROUP_ID:
        return

    if message.message_thread_id is None:
        await message.reply("❌ Bu buyruq faqat topic ichida ishlaydi")
        return

    topic_id = message.message_thread_id

    add_product_flow[topic_id] = {
        "step": "photo",
        "admin_id": message.from_user.id
    }

    await message.answer(
        "🖼 Mahsulot rasmini yuboring",
        message_thread_id=topic_id
    )


@router.message()
async def add_product_steps(message: Message, bot: Bot):
    if message.chat.id != MARKET_GROUP_ID:
        return

    topic_id = message.message_thread_id
    if topic_id not in add_product_flow:
        return

    flow = add_product_flow[topic_id]

    # ❗ faqat bot xabariga reply bo‘lsa ishlaydi
    if not message.reply_to_message:
        return

    # 1️⃣ RASM
    if flow["step"] == "photo":
        if not message.photo:
            await message.reply("❌ Iltimos, rasm yuboring")
            return

        flow["photo"] = message.photo[-1].file_id
        flow["step"] = "description"

        await message.answer(
            "📝 Mahsulot tavsifini yuboring",
            message_thread_id=topic_id
        )
        return

    # 2️⃣ TAVSIF
    if flow["step"] == "description":
        if not message.text:
            await message.reply("❌ Matn yuboring")
            return

        flow["description"] = message.text
        flow["step"] = "product_id"

        await message.answer(
            "🆔 Mahsulot ID raqamini yuboring",
            message_thread_id=topic_id
        )
        return

    # 3️⃣ ID → ELON
    if flow["step"] == "product_id":
        if not message.text:
            await message.reply("❌ ID raqam bo‘lishi kerak")
            return

        product_id = message.text.strip()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Buyurtma berish",
                        url=f"https://t.me/{BOT_USERNAME}?start=order_{product_id}"
                    )
                ]
            ]
        )

        await bot.send_photo(
            chat_id=MARKET_GROUP_ID,
            message_thread_id=topic_id,
            photo=flow["photo"],
            caption=f"{flow['description']}\n\n🆔 ID: {product_id}",
            reply_markup=keyboard
        )

        await message.answer(
            "✅ Mahsulot muvaffaqiyatli joylandi",
            message_thread_id=topic_id
        )

        del add_product_flow[topic_id]
