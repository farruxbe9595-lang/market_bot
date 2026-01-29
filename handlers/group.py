from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_USERNAME

router = Router()

# vaqtinchalik xotira (FSM o‘rniga)
ADD_PRODUCT = {}


@router.message(F.text == "/add_product")
async def add_product_cmd(message: Message):
    # faqat topic ichida
    if message.message_thread_id is None:
        await message.reply("❌ /add_product faqat topic ichida ishlaydi")
        return

    topic_id = message.message_thread_id

    ADD_PRODUCT[topic_id] = {
        "step": "photo"
    }

    bot_msg = await message.reply(
        "🖼 Mahsulot rasmini yuboring\n\n"
        "❗️Shu xabarga reply qilib yuboring"
    )

    ADD_PRODUCT[topic_id]["bot_msg_id"] = bot_msg.message_id


@router.message(F.reply_to_message)
async def add_product_steps(message: Message):
    if message.message_thread_id is None:
        return

    topic_id = message.message_thread_id

    if topic_id not in ADD_PRODUCT:
        return

    data = ADD_PRODUCT[topic_id]

    # faqat bot yozgan xabarga reply bo‘lsa
    if message.reply_to_message.message_id != data.get("bot_msg_id"):
        return

    # 1️⃣ RASM
    if data["step"] == "photo":
        if not message.photo:
            await message.reply("❌ Rasm yuboring")
            return

        data["photo"] = message.photo[-1].file_id
        data["step"] = "desc"

        bot_msg = await message.reply(
            "📝 Mahsulot tavsifini yuboring\n\n"
            "❗️Shu xabarga reply qiling"
        )
        data["bot_msg_id"] = bot_msg.message_id
        return

    # 2️⃣ TAVSIF
    if data["step"] == "desc":
        if not message.text:
            await message.reply("❌ Tavsif matn bo‘lishi kerak")
            return

        data["desc"] = message.text
        data["step"] = "id"

        bot_msg = await message.reply(
            "🆔 Mahsulot ID raqamini yuboring\n\n"
            "❗️Shu xabarga reply qiling"
        )
        data["bot_msg_id"] = bot_msg.message_id
        return

    # 3️⃣ ID
    if data["step"] == "id":
        product_id = message.text.strip()

        if not product_id.isdigit():
            await message.reply("❌ ID faqat raqam bo‘lishi kerak")
            return

        # BUYURTMA TUGMASI
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

        await message.bot.send_photo(
            chat_id=message.chat.id,
            message_thread_id=topic_id,
            photo=data["photo"],
            caption=(
                f"📦 <b>Mahsulot</b>\n\n"
                f"{data['desc']}\n\n"
                f"🆔 ID: <code>{product_id}</code>"
            ),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await message.reply("✅ Mahsulot e’lon qilindi")

        ADD_PRODUCT.pop(topic_id, None)
