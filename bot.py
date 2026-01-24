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
ALLOWED_TOPIC_ID = 1  # 💬 Muhokama chat


# ================= ADMIN CHECK =================
async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)



# ================= ADMIN CLEANUP =================
async def cleanup_messages(chat_id: int, msg_ids: list[int]):
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass


# ================= /add_product =================
# ================= ADD PRODUCT FSM =================

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


class AddProductState(StatesGroup):
    photo = State()
    text = State()
    product_id = State()


def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin")]
        ]
    )


@dp.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    if message.chat.id != MARKET_GROUP_ID:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if message.message_thread_id is None:
        await message.answer("❗ Mahsulotni faqat topic ichida qo‘shing.")
        return

    await state.clear()

    # 🔥 msgs ni darrov to‘ldiramiz
    msg = await message.answer(
        "🖼 Mahsulot rasmini yuboring:",
        reply_markup=admin_cancel_kb()
    )

    await state.update_data(
        topic_id=message.message_thread_id,
        msgs=[msg.message_id]
    )

    await state.set_state(AddProductState.photo)



# ---------- PHOTO ----------
@dp.message(StateFilter(AddProductState.photo), F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    await state.update_data(
        product_photo=message.photo[-1].file_id,
        msgs=data["msgs"]
    )

    msg = await message.answer(
        "📝 Tavsifni yuboring:",
        reply_markup=admin_cancel_kb()
    )

    data["msgs"].append(msg.message_id)
    await state.update_data(msgs=data["msgs"])

    await state.set_state(AddProductState.text)


@dp.message(StateFilter(AddProductState.photo))
async def add_product_photo_invalid(message: Message):
    await message.answer("❗ Iltimos, rasm yuboring.")


# ---------- TEXT ----------
@dp.message(StateFilter(AddProductState.text), F.text)
async def add_product_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    await state.update_data(
        product_text=message.text,
        msgs=data["msgs"]
    )

    msg = await message.answer(
        "🆔 Mahsulot ID ni yuboring:",
        reply_markup=admin_cancel_kb()
    )

    data["msgs"].append(msg.message_id)
    await state.update_data(msgs=data["msgs"])

    await state.set_state(AddProductState.product_id)


# ---------- PRODUCT ID ----------
@dp.message(StateFilter(AddProductState.product_id), F.text)
async def add_product_publish(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    # 🔐 HIMOYA: bot username hali olinmagan bo‘lsa
    if not BOT_USERNAME:
        await message.answer(
            "❗ Bot username hali yuklanmadi.\n"
            "⏳ Iltimos, 2–3 soniya kutib qayta urinib ko‘ring."
        )
        return

    product_id = message.text.strip()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Buyurtma berish",
                    url=f"https://t.me/{BOT_USERNAME}?start={product_id}"

                )
            ]
        ]
    )

    await bot.send_photo(
        chat_id=MARKET_GROUP_ID,
        message_thread_id=data["topic_id"],
        photo=data["product_photo"],
        caption=f"🆔 ID: {product_id}\n\n{data['product_text']}",
        reply_markup=kb
    )

    # 🔥 Tozalash
    for mid in data["msgs"]:
        try:
            await bot.delete_message(message.chat.id, mid)
        except:
            pass

    await state.clear()


# ---------- CANCEL ----------
@dp.callback_query(F.data == "cancel_admin")
async def cancel_add_product(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    for mid in data.get("msgs", []):
        try:
            await bot.delete_message(call.message.chat.id, mid)
        except:
            pass

    await state.clear()
    await call.answer("Bekor qilindi")

# ================= ORDER STORAGE =================
ORDERS: dict[int, dict] = {}
# ================= ORDER FLOW (FINAL FIX) =================
# ================= ORDER START =================
@dp.message(CommandStart())
async def start_plain(message: Message):
    await message.answer(
        "🛒 Buyurtma berish uchun mahsulotdagi\n"
        "«🛒 Buyurtma berish» tugmasini bosing."
    )

@dp.message(CommandStart(deep_link=True))
async def start_order(message: Message):
    user_id = message.from_user.id

    # eski buyurtmani tozalash
    ORDERS.pop(user_id, None)

    # 🔐 deep link tekshiruvi
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🛒 Buyurtma berish uchun mahsulotdagi\n"
            "«🛒 Buyurtma berish» tugmasini bosing."
        )
        return

    product_id = parts[1].strip()

    ORDERS[user_id] = {
        "product_id": product_id,
        "step": "size"
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("👕 M", callback_data="size:M"),
            InlineKeyboardButton("👕 L", callback_data="size:L"),
            InlineKeyboardButton("👕 XL", callback_data="size:XL")
        ],
        [
            InlineKeyboardButton("🧒 3–4 yosh", callback_data="size:3-4"),
            InlineKeyboardButton("🧒 5–6 yosh", callback_data="size:5-6"),
            InlineKeyboardButton("🧒 7–8 yosh", callback_data="size:7-8")
        ],
        [
            InlineKeyboardButton("🧒 9–10 yosh", callback_data="size:9-10"),
            InlineKeyboardButton("🧒 11–12 yosh", callback_data="size:11-12")
        ],
        [
            InlineKeyboardButton("👟 36", callback_data="size:36"),
            InlineKeyboardButton("👟 37", callback_data="size:37"),
            InlineKeyboardButton("👟 38", callback_data="size:38")
        ],
        [
            InlineKeyboardButton("👟 39", callback_data="size:39"),
            InlineKeyboardButton("👟 40", callback_data="size:40"),
            InlineKeyboardButton("👟 41", callback_data="size:41")
        ],
        [
            InlineKeyboardButton("👟 42", callback_data="size:42"),
            InlineKeyboardButton("👟 43", callback_data="size:43"),
            InlineKeyboardButton("👟 44", callback_data="size:44")
        ],
        [
            InlineKeyboardButton("📦 O‘lcham kerak emas", callback_data="size:none")
        ]
    ])

    await message.answer(
        "👕 O‘lchamni tanlang:",
        reply_markup=kb
    )


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

    await message.answer(
        "✅ Buyurtma qabul qilindi!",
        reply_markup=ReplyKeyboardRemove()
    )


# ================= TOPIC WRITE GUARD =================
@dp.message(F.chat.id == MARKET_GROUP_ID, F.text)
async def topic_guard(message: Message, state: FSMContext):

    # FSM jarayonida bo‘lsa — tegma
    if await state.get_state():
        return

    # Admin bo‘lsa — tegma
    if await is_admin(message.chat.id, message.from_user.id):
        return

    # /start va boshqa buyruqlarga UMUMAN TEGMA
    if message.text and message.text.startswith("/"):
        return


    # Topic bo‘lmagan joy (masalan, service message) — tegma
    if message.message_thread_id is None:
        return

    # ✅ FAQAT MUHOKAMA CHATGA RUXSAT
    if message.message_thread_id == ALLOWED_TOPIC_ID:
        return

    # ❌ QOLGAN TOPICLARDA — O‘CHIR + OGOHLANTIR
    try:
        await message.delete()

        warn = await message.answer(
            "⚠️ <b>Diqqat!</b>\n\n"
            "❌ Bu bo‘limda yozish taqiqlangan.\n"
            "✍️ Fikr va savollarni faqat\n"
            "💬 <b>Muhokama chat</b> da yozing.",
            parse_mode="HTML"
        )

        # ogohlantirishni 5 soniyadan keyin o‘chiramiz
        await asyncio.sleep(5)
        await warn.delete()

    except:
        pass


# ================= RUN =================
BOT_USERNAME = None

async def main():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

