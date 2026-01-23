import asyncio
import sys
import os

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    CallbackQuery
)
from aiogram.filters import Command, CommandStart

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

MARKET_GROUP_ID = -1003618675735
ADMIN_CHANNEL_ID = -1003631320685

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

DISCUSSION_TOPIC_ID = 1  # Muhokama chat

# ================= ADMIN CHECK =================
async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

# ================= ORDER STORAGE =================
ORDERS: dict[int, dict] = {}

# ================= ORDER START =================
@dp.message(CommandStart())
async def start_order(message: Message):
    if " " not in message.text:
        await message.answer("🛒 Buyurtma berish uchun mahsulotdagi tugmani bosing.")
        return

    product_id = message.text.split(" ", 1)[1]
    user_id = message.from_user.id

    ORDERS[user_id] = {
        "product_id": product_id,
        "step": "size"
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("👕 M", callback_data="size:M"),
         InlineKeyboardButton("👕 L", callback_data="size:L"),
         InlineKeyboardButton("👕 XL", callback_data="size:XL")],

        [InlineKeyboardButton("🧒 3–4 yosh", callback_data="size:3-4"),
         InlineKeyboardButton("🧒 5–6 yosh", callback_data="size:5-6"),
         InlineKeyboardButton("🧒 7–8 yosh", callback_data="size:7-8")],

        [InlineKeyboardButton("🧒 9–10 yosh", callback_data="size:9-10"),
         InlineKeyboardButton("🧒 11–12 yosh", callback_data="size:11-12")],

        [InlineKeyboardButton("👟 36", callback_data="size:36"),
         InlineKeyboardButton("👟 37", callback_data="size:37"),
         InlineKeyboardButton("👟 38", callback_data="size:38")],

        [InlineKeyboardButton("👟 39", callback_data="size:39"),
         InlineKeyboardButton("👟 40", callback_data="size:40"),
         InlineKeyboardButton("👟 41", callback_data="size:41")],

        [InlineKeyboardButton("👟 42", callback_data="size:42"),
         InlineKeyboardButton("👟 43", callback_data="size:43"),
         InlineKeyboardButton("👟 44", callback_data="size:44")],

        [InlineKeyboardButton("📦 O‘lcham kerak emas", callback_data="size:none")]
    ])

    await message.answer("👕 O‘lchamni tanlang:", reply_markup=kb)

# ================= SIZE =================
@dp.callback_query(F.data.startswith("size:"))
async def choose_size(call: CallbackQuery):
    user_id = call.from_user.id
    data = ORDERS.get(user_id)

    if not data or data.get("step") != "size":
        await call.answer("Bu qadam o‘tilgan", show_alert=True)
        return

    size = call.data.split(":", 1)[1]
    data["size"] = "Kerak emas" if size == "none" else size
    data["step"] = "qty"

    await call.message.edit_reply_markup(reply_markup=None)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("1", callback_data="qty:1"),
         InlineKeyboardButton("2", callback_data="qty:2"),
         InlineKeyboardButton("3", callback_data="qty:3")],

        [InlineKeyboardButton("4", callback_data="qty:4"),
         InlineKeyboardButton("5", callback_data="qty:5"),
         InlineKeyboardButton("6", callback_data="qty:6")],

        [InlineKeyboardButton("7", callback_data="qty:7"),
         InlineKeyboardButton("8", callback_data="qty:8"),
         InlineKeyboardButton("9", callback_data="qty:9"),
         InlineKeyboardButton("10", callback_data="qty:10")]
    ])

    await call.message.edit_text("📦 Nechta dona?", reply_markup=kb)

# ================= QUANTITY =================
@dp.callback_query(F.data.startswith("qty:"))
async def choose_quantity(call: CallbackQuery):
    user_id = call.from_user.id
    data = ORDERS.get(user_id)

    if not data or data.get("step") != "qty":
        await call.answer("Bu qadam o‘tilgan", show_alert=True)
        return

    data["quantity"] = call.data.split(":", 1)[1]
    data["step"] = "phone"

    await call.message.edit_reply_markup(reply_markup=None)

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

# ================= FINISH =================
@dp.message(F.contact)
async def finish_order(message: Message):
    user_id = message.from_user.id
    data = ORDERS.get(user_id)

    if not data or data.get("step") != "phone":
        return

    ORDERS.pop(user_id, None)

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"

    profile_url = (
        f"https://t.me/{message.from_user.username}"
        if message.from_user.username
        else f"tg://user?id={user_id}"
    )

    text = (
        "🛒 <b>YANGI BUYURTMA</b>\n\n"
        f"🆔 <b>Mahsulot:</b> {data['product_id']}\n"
        f"👕 <b>O‘lcham:</b> {data['size']}\n"
        f"📦 <b>Soni:</b> {data['quantity']}\n\n"
        f"📞 <b>Tel:</b> <a href='tel:{phone}'>{phone}</a>"
    )

    await bot.send_message(
        ADMIN_CHANNEL_ID,
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("✉️ Buyurtmachiga yozish", url=profile_url)],
                [InlineKeyboardButton("📞 Qo‘ng‘iroq qilish", url=f"tel:{phone}")]
            ]
        )
    )

    await message.answer("✅ Buyurtma qabul qilindi!", reply_markup=ReplyKeyboardRemove())

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
