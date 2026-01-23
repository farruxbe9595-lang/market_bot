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
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


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

# ================= STATES =================
class AddProductState(StatesGroup):
    photo = State()
    text = State()
    product_id = State()

class OrderState(StatesGroup):
    size = State()
    quantity = State()
    phone = State()

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
            [KeyboardButton(text="➕ Boshqa son kiritish")],
            [KeyboardButton(text="❌ Buyurtmani bekor qilish")]
        ],
        resize_keyboard=True
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

# ================= ORDER FLOW (O‘ZGARMAGAN) =================
@dp.message(CommandStart())
async def start_order(message: Message, state: FSMContext):
    await state.clear()

    if " " not in message.text:
        await message.answer("🛒 Buyurtma berish uchun mahsulotdagi tugmani bosing.")
        return

    product_id = message.text.split(" ", 1)[1]
    await state.update_data(product_id=product_id, user_id=message.from_user.id, username=message.from_user.username)

    await message.answer("👕 O‘lchamni tanlang:", reply_markup=size_kb())
    await state.set_state(OrderState.size)

@dp.message(F.text == "❌ Buyurtmani bekor qilish")
@dp.message(Command("cancel"))
async def cancel_order(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())

@dp.message(StateFilter(OrderState.size), F.text)
async def order_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("📦 Nechta dona?", reply_markup=quantity_kb())
    await state.set_state(OrderState.quantity)

@dp.message(OrderState.quantity, F.text.in_([str(i) for i in range(1, 11)]))
async def quantity_btn(message: Message, state: FSMContext):
    await state.update_data(quantity=message.text)
    await message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=phone_kb())
    await state.set_state(OrderState.phone)

@dp.message(OrderState.quantity, F.text == "➕ Boshqa son kiritish")
async def quantity_custom(message: Message, state: FSMContext):
    await message.answer("✍️ Sonni yozing:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderState.quantity)  # 🔒 MUHIM

@dp.message(StateFilter(OrderState.quantity), F.text)
async def quantity_text(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return
    await state.update_data(quantity=message.text)
    await message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=phone_kb())
    await state.set_state(OrderState.phone)
    
@dp.message(StateFilter(OrderState.phone), F.contact)
async def order_finish(message: Message, state: FSMContext):
    data = await state.get_data()

    # 🔒 DOUBLE TRIGGER BLOKI
    if data.get("_finished"):
        return

    await state.update_data(_finished=True)

    profile_url = (
        f"https://t.me/{data['username']}"
        if data.get("username")
        else f"tg://user?id={data['user_id']}"
    )

    raw_phone = message.contact.phone_number.strip()
    phone = raw_phone if raw_phone.startswith("+") else f"+{raw_phone}"

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
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Buyurtmachiga yozish", url=profile_url)],
                [InlineKeyboardButton(text="📞 Qo‘ng‘iroq qilish", url=f"tel:{phone}")]
            ]
        )
    )

    await message.answer("✅ Buyurtma qabul qilindi!", reply_markup=ReplyKeyboardRemove())

    # 🔥 FSMNI KECHIKTIRIB YOPAMIZ
    await asyncio.sleep(0.3)
    await state.clear()

@dp.message(StateFilter(OrderState.phone), F.text)
async def order_phone_invalid(message: Message):
    await message.answer(
        "📞 Iltimos, telefon raqamingizni *tugma orqali* yuboring.",
        parse_mode="Markdown"
    )




# ================= TOPIC WRITE GUARD =================
@dp.message(
    F.chat.id == MARKET_GROUP_ID,
    StateFilter(None)
)
async def topic_write_guard(message: Message):
    # ❌ CONTACT SERVICE UPDATE HAM TEGMASIN
    if message.contact is not None:
        return

    if message.message_thread_id is None:
        return

    if message.message_thread_id == DISCUSSION_TOPIC_ID:
        return

    if message.text and message.text.startswith("/"):
        return

    if (
        message.photo
        or message.document
        or message.video
        or message.location
    ):
        return

    try:
        await message.delete()
    except:
        pass

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
