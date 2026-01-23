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

# ================= TOPIC RULES =================
DISCUSSION_TOPIC_ID = 1  # Muhokama chat

# ================= ADMIN CHECK =================
async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

# ================= KEYBOARDS =================
def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin")]]
    )

def size_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👕 M"), KeyboardButton(text="👕 L"), KeyboardButton(text="👕 XL")],
            [KeyboardButton(text="🧒 3–4 yosh"), KeyboardButton(text="🧒 5–6 yosh"), KeyboardButton(text="🧒 7–8 yosh")],
            [KeyboardButton(text="🧒 9–10 yosh"), KeyboardButton(text="🧒 11–12 yosh")],
            [KeyboardButton(text="👟 36"), KeyboardButton(text="👟 37"), KeyboardButton(text="👟 38")],
            [KeyboardButton(text="👟 39"), KeyboardButton(text="👟 40"), KeyboardButton(text="👟 41")],
            [KeyboardButton(text="👟 42"), KeyboardButton(text="👟 43"), KeyboardButton(text="👟 44"), KeyboardButton(text="👟 45")],
            [KeyboardButton(text="📦 O‘lcham kerak emas")],
            [KeyboardButton(text="❌ Buyurtmani bekor qilish")]
        ],
        resize_keyboard=True
    )

def quantity_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 11)],
            [KeyboardButton(text="❌ Buyurtmani bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# ================= ADMIN CLEANUP =================
async def cleanup_messages(chat_id: int, msg_ids: list[int]):
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass


# ================= /add_product =================
@dp.message(Command("add_product"))
async def add_product(message: Message, state: FSMContext):
    if message.chat.id != MARKET_GROUP_ID:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if message.message_thread_id is None:
        await message.answer("❗ Topic ichida yozing.")
        return

    await state.clear()
    await state.update_data(
        topic_id=message.message_thread_id,
        msgs=[message.message_id]
    )

    msg = await message.answer("🖼 Mahsulot rasmini yuboring:", reply_markup=admin_cancel_kb())
    await state.update_data(msgs=[message.message_id, msg.message_id])
    await state.set_state(AddProductState.photo)

@dp.message(StateFilter(AddProductState.photo), F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    await state.update_data(
        product_photo=message.photo[-1].file_id,
        msgs=data["msgs"]
    )

    msg = await message.answer("📝 Tavsifni yuboring:", reply_markup=admin_cancel_kb())
    data["msgs"].append(msg.message_id)
    await state.update_data(msgs=data["msgs"])
    await state.set_state(AddProductState.text)

@dp.message(StateFilter(AddProductState.photo))
async def add_product_photo_invalid(message: Message):
    await message.answer("❗ Iltimos, mahsulot rasmini yuboring.")

@dp.message(StateFilter(AddProductState.text), F.text)
async def add_product_text(message: Message, state: FSMContext):

    data = await state.get_data()
    data["msgs"].append(message.message_id)

    await state.update_data(product_text=message.text, msgs=data["msgs"])

    msg = await message.answer("🆔 Mahsulot ID yozing:", reply_markup=admin_cancel_kb())
    data["msgs"].append(msg.message_id)
    await state.update_data(msgs=data["msgs"])
    await state.set_state(AddProductState.product_id)

@dp.message(StateFilter(AddProductState.product_id), F.text)
async def add_product_publish(message: Message, state: FSMContext):

    data = await state.get_data()
    data["msgs"].append(message.message_id)

    product_id = message.text.strip()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🛒 Buyurtma berish",
                url=f"https://t.me/{(await bot.me()).username}?start={product_id}"
            )
        ]]
    )

    await bot.send_photo(
        chat_id=MARKET_GROUP_ID,
        message_thread_id=data["topic_id"],
        photo=data["product_photo"],
        caption=f"🆔 ID: {product_id}\n\n{data['product_text']}",
        reply_markup=kb
    )

    await cleanup_messages(message.chat.id, data["msgs"])
    await state.clear()

@dp.callback_query(F.data == "cancel_admin")
async def cancel_admin(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await cleanup_messages(call.message.chat.id, data.get("msgs", []))
    await state.clear()
    await call.answer("Bekor qilindi")

# ================= ORDER FLOW (FINAL FIX) =================
ORDERS: dict[int, dict] = {}

@dp.message(CommandStart())
async def start_order(message: Message):
    if " " not in message.text:
        await message.answer("🛒 Buyurtma berish uchun mahsulotdagi tugmani bosing.")
        return

    product_id = message.text.split(" ", 1)[1]

    ORDERS[message.from_user.id] = {
        "product_id": product_id
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        # 👕 Kiyim
        [
            InlineKeyboardButton(text="👕 M", callback_data="size:M"),
            InlineKeyboardButton(text="👕 L", callback_data="size:L"),
            InlineKeyboardButton(text="👕 XL", callback_data="size:XL"),
        ],
        # 🧒 Bolalar yoshi
        [
            InlineKeyboardButton(text="🧒 3–4 yosh", callback_data="size:3-4"),
            InlineKeyboardButton(text="🧒 5–6 yosh", callback_data="size:5-6"),
            InlineKeyboardButton(text="🧒 7–8 yosh", callback_data="size:7-8"),
        ],
        [
            InlineKeyboardButton(text="🧒 9–10 yosh", callback_data="size:9-10"),
            InlineKeyboardButton(text="🧒 11–12 yosh", callback_data="size:11-12"),
        ],
        # 👟 Oyoq kiyim
        [
            InlineKeyboardButton(text="👟 36", callback_data="size:36"),
            InlineKeyboardButton(text="👟 37", callback_data="size:37"),
            InlineKeyboardButton(text="👟 38", callback_data="size:38"),
        ],
        [
            InlineKeyboardButton(text="👟 39", callback_data="size:39"),
            InlineKeyboardButton(text="👟 40", callback_data="size:40"),
            InlineKeyboardButton(text="👟 41", callback_data="size:41"),
        ],
        [
            InlineKeyboardButton(text="👟 42", callback_data="size:42"),
            InlineKeyboardButton(text="👟 43", callback_data="size:43"),
            InlineKeyboardButton(text="👟 44", callback_data="size:44"),
        ],
        # 📦 O‘lcham yo‘q
        [
            InlineKeyboardButton(
                text="📦 O‘lcham kerak emas",
                callback_data="size:none"
            )
        ]
    ])

    await message.answer("👕 O‘lchamni tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("size:"))
async def choose_size(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id not in ORDERS:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return

    size = call.data.split(":", 1)[1]
    ORDERS[user_id]["size"] = "Kerak emas" if size == "none" else size

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="qty:1"),
            InlineKeyboardButton(text="2", callback_data="qty:2"),
            InlineKeyboardButton(text="3", callback_data="qty:3"),
        ],
        [
            InlineKeyboardButton(text="4", callback_data="qty:4"),
            InlineKeyboardButton(text="5", callback_data="qty:5"),
            InlineKeyboardButton(text="6", callback_data="qty:6"),
        ],
        [
            InlineKeyboardButton(text="7", callback_data="qty:7"),
            InlineKeyboardButton(text="8", callback_data="qty:8"),
            InlineKeyboardButton(text="9", callback_data="qty:9"),
            InlineKeyboardButton(text="10", callback_data="qty:10"),
        ]
    ])

    await call.message.edit_text("📦 Nechta dona?", reply_markup=kb)
@dp.callback_query(F.data.startswith("qty:"))
async def choose_quantity(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id not in ORDERS:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return

    qty = call.data.split(":", 1)[1]
    ORDERS[user_id]["quantity"] = qty

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
@dp.message(F.contact)
async def finish_order(message: Message):
    user_id = message.from_user.id
    data = ORDERS.pop(user_id, None)

    if not data:
        return

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
                [InlineKeyboardButton(text="✉️ Buyurtmachiga yozish", url=profile_url)],
                [InlineKeyboardButton(text="📞 Qo‘ng‘iroq qilish", url=f"tel:{phone}")]
            ]
        )
    )

    await message.answer(
        "✅ Buyurtma qabul qilindi!",
        reply_markup=ReplyKeyboardRemove()
    )

# ================= TOPIC WRITE GUARD =================
@dp.message(
    F.chat.id == MARKET_GROUP_ID,
    StateFilter(None)   # FSM YO‘Q PAYTDA GINA
)
async def topic_write_guard(message: Message):
    if message.message_thread_id is None:
        return

    if message.message_thread_id == DISCUSSION_TOPIC_ID:
        return

    if message.text and message.text.startswith("/"):
        return

    if await is_admin(message.chat.id, message.from_user.id):
        return
 


    # User xabarini o‘chiramiz
    try:
        await message.delete()
    except:
        pass

    # Ogohlantirish yuboramiz
    try:
        warn = await message.answer(
            "❌ Bu bo‘limda faqat buyurtma berishingiz mumkin.\n"
            "💬 Muhokama uchun *Muhokama chat*dan foydalaning.",
            parse_mode="Markdown"
        )
        await asyncio.sleep(3)
        await warn.delete()
    except:
        pass


# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
