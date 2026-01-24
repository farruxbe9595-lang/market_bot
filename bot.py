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
ORDERS: dict[int, dict] = {}

def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin")]
        ]
    )


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

# ================= TOPIC WRITE CONTROL (TO‘G‘RILANGAN) =================
@dp.message(
    F.chat.id == MARKET_GROUP_ID,
    F.from_user.is_bot == False
)
async def topic_write_guard(message: Message, state: FSMContext):
    # FSM ishlayapti — aralashmaymiz
    if await state.get_state() is not None:
        return

    # Topic bo‘lmasa — chiqib ket
    if message.message_thread_id is None:
        return

    topic_id = message.message_thread_id

    # Muhokama topic — ruxsat
    if topic_id == DISCUSSION_TOPIC_ID:
        return

    # Admin bo‘lsa — ruxsat
    if await is_admin(message.chat.id, message.from_user.id):
        return

    # Oddiy user yozdi — o‘chiramiz
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

@dp.message(AddProductState.photo, F.photo)
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

@dp.message(AddProductState.text, F.text)
async def add_product_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    await state.update_data(product_text=message.text, msgs=data["msgs"])

    msg = await message.answer("🆔 Mahsulot ID yozing:", reply_markup=admin_cancel_kb())
    data["msgs"].append(msg.message_id)
    await state.update_data(msgs=data["msgs"])
    await state.set_state(AddProductState.product_id)

@dp.message(AddProductState.product_id, F.text)
async def add_product_publish(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    product_id = message.text.strip()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🛒 Buyurtma berish",
                callback_data=f"order:{product_id}"

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

# ================= ORDER FLOW (O‘ZGARMAGAN) =================
ORDERS: dict[int, dict] = {}
@dp.callback_query(F.data.startswith("order:"))
async def order_start(call: CallbackQuery):
    user_id = call.from_user.id
    product_id = call.data.split(":", 1)[1]

    # eski buyurtma bo‘lsa — tozalaymiz
    ORDERS[user_id] = {
        "product_id": product_id
    }

    await call.message.answer(
        "👕 O‘lchamni tanlang:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("👕 M", callback_data="size:M"),
                    InlineKeyboardButton("👕 L", callback_data="size:L"),
                    InlineKeyboardButton("👕 XL", callback_data="size:XL"),
                ],
                [
                    InlineKeyboardButton("📦 O‘lcham kerak emas", callback_data="size:none")
                ]
            ]
        )
    )

    await call.answer()
@dp.callback_query(F.data.startswith("size:"))
async def choose_size(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id not in ORDERS:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return

    size = call.data.split(":", 1)[1]
    ORDERS[user_id]["size"] = "Kerak emas" if size == "none" else size

    await call.message.edit_text(
        "📦 Nechta dona?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("1", callback_data="qty:1"),
                    InlineKeyboardButton("2", callback_data="qty:2"),
                    InlineKeyboardButton("3", callback_data="qty:3"),
                ],
                [
                    InlineKeyboardButton("4", callback_data="qty:4"),
                    InlineKeyboardButton("5", callback_data="qty:5"),
                ]
            ]
        )
    )

    await call.answer()
@dp.callback_query(F.data.startswith("qty:"))
async def choose_qty(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id not in ORDERS:
        return

    ORDERS[user_id]["quantity"] = call.data.split(":", 1)[1]

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    await call.answer()
@dp.message(F.contact)
async def finish_order(message: Message):
    user_id = message.from_user.id
    data = ORDERS.pop(user_id, None)

    if not data:
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"

    await bot.send_message(
        ADMIN_CHANNEL_ID,
        f"🛒 YANGI BUYURTMA\n\n"
        f"🆔 Mahsulot: {data['product_id']}\n"
        f"👕 O‘lcham: {data['size']}\n"
        f"📦 Soni: {data['quantity']}\n"
        f"📞 Tel: {phone}"
    )

    await message.answer("✅ Buyurtma qabul qilindi!", reply_markup=ReplyKeyboardRemove())

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
