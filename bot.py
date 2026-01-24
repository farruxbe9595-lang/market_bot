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
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

MARKET_GROUP_ID = -1003618675735
ADMIN_CHANNEL_ID = -1003631320685
DISCUSSION_TOPIC_ID = 1  # Muhokama chat

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================= STORAGE =================
ORDERS: dict[int, dict] = {}

# ================= FSM (ADMIN ONLY) =================
class AddProductState(StatesGroup):
    photo = State()
    text = State()
    product_id = State()

# ================= HELPERS =================
def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_admin")]]
    )

async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

async def cleanup_messages(chat_id: int, msg_ids: list[int]):
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass

# ================= ADD PRODUCT (ADMIN FSM) =================
@dp.message(Command("add_product"))
async def add_product(message: Message, state: FSMContext):
    if message.chat.id != MARKET_GROUP_ID:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if message.message_thread_id is None:
        await message.answer("❗ Mahsulotni faqat topic ichida qo‘shing.")
        return

    await state.clear()
    msg = await message.answer("🖼 Mahsulot rasmini yuboring:", reply_markup=admin_cancel_kb())
    await state.update_data(
        topic_id=message.message_thread_id,
        msgs=[message.message_id, msg.message_id]
    )
    await state.set_state(AddProductState.photo)

@dp.message(AddProductState.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    msg = await message.answer("📝 Tavsifni yuboring:", reply_markup=admin_cancel_kb())
    await state.update_data(
        product_photo=message.photo[-1].file_id,
        msgs=data["msgs"] + [msg.message_id]
    )
    await state.set_state(AddProductState.text)

@dp.message(AddProductState.text, F.text)
async def add_product_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    msg = await message.answer("🆔 Mahsulot ID yozing:", reply_markup=admin_cancel_kb())
    await state.update_data(
        product_text=message.text,
        msgs=data["msgs"] + [msg.message_id]
    )
    await state.set_state(AddProductState.product_id)

@dp.message(AddProductState.product_id, F.text)
async def add_product_publish(message: Message, state: FSMContext):
    data = await state.get_data()
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

# ================= ORDER FLOW (NO FSM, TELEGRAM SAFE) =================
@dp.callback_query(F.data.startswith("order:"))
async def order_start(call: CallbackQuery):
    user_id = call.from_user.id
    product_id = call.data.split(":", 1)[1]

    ORDERS[user_id] = {
        "product_id": product_id,
        "step": "size"
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
                [InlineKeyboardButton("📦 O‘lcham kerak emas", callback_data="size:none")]
            ]
        )
    )
    await call.answer()

@dp.callback_query(F.data.startswith("size:"))
async def choose_size(call: CallbackQuery):
    data = ORDERS.get(call.from_user.id)
    if not data or data.get("step") != "size":
        return

    data["size"] = "Kerak emas" if call.data.endswith("none") else call.data.split(":")[1]
    data["step"] = "qty"

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
    data = ORDERS.get(call.from_user.id)
    if not data or data.get("step") != "qty":
        return

    data["quantity"] = call.data.split(":")[1]
    data["step"] = "phone"

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring (botga shaxsiy chatda):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="📞 Botga o‘tish",
                    url=f"https://t.me/{(await bot.get_me()).username}"
                )
            ]]
        )
    )
    await call.answer()

# ================= PRIVATE CONTACT =================
@dp.message(F.contact)
async def finish_order(message: Message):
    data = ORDERS.pop(message.from_user.id, None)
    if not data or data.get("step") != "phone":
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = f"+{phone}"

    await bot.send_message(
        ADMIN_CHANNEL_ID,
        f"🛒 <b>YANGI BUYURTMA</b>\n\n"
        f"🆔 <b>Mahsulot:</b> {data['product_id']}\n"
        f"👕 <b>O‘lcham:</b> {data['size']}\n"
        f"📦 <b>Soni:</b> {data['quantity']}\n"
        f"📞 <b>Tel:</b> {phone}",
        parse_mode="HTML"
    )

    await message.answer(
        "✅ Buyurtma qabul qilindi!\nOperatorlar siz bilan bog‘lanadi.",
        reply_markup=ReplyKeyboardRemove()
    )

# ================= TOPIC WRITE GUARD (LAST) =================
@dp.message(F.chat.id == MARKET_GROUP_ID, F.text)
async def topic_guard(message: Message, state: FSMContext):
    if await state.get_state():
        return
    if message.message_thread_id is None:
        return
    if message.message_thread_id == DISCUSSION_TOPIC_ID:
        return
    if await is_admin(message.chat.id, message.from_user.id):
        return
    if message.text.startswith("/"):
        return

    try:
        await message.delete()
        warn = await message.answer(
            "❌ Bu bo‘limda yozish taqiqlangan.\n"
            "💬 Fikrlar faqat *Muhokama chat*da.",
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
