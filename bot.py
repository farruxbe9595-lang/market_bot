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
DISCUSSION_TOPIC_ID = 1  # 💬 Muhokama chat

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================= FSM (ADMIN) =================
class AddProductState(StatesGroup):
    photo = State()
    text = State()
    product_id = State()

# ================= HELPERS =================
def cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_add")]
        ]
    )

async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

async def cleanup(chat_id: int, msg_ids: list[int]):
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass

# ================= /add_product (ADMIN) =================
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

    msg = await message.answer(
        "🖼 Mahsulot rasmini yuboring:",
        reply_markup=cancel_kb()
    )

    await state.update_data(
        topic_id=message.message_thread_id,
        msgs=[msg.message_id]
    )
    await state.set_state(AddProductState.photo)

@dp.message(AddProductState.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    msg = await message.answer(
        "📝 Tavsifni yuboring:",
        reply_markup=cancel_kb()
    )

    await state.update_data(
        product_photo=message.photo[-1].file_id,
        msgs=data["msgs"] + [msg.message_id]
    )
    await state.set_state(AddProductState.text)

@dp.message(AddProductState.text, F.text)
async def add_product_text(message: Message, state: FSMContext):
    data = await state.get_data()
    data["msgs"].append(message.message_id)

    msg = await message.answer(
        "🆔 Mahsulot ID ni yuboring:",
        reply_markup=cancel_kb()
    )

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
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buyurtma berish", callback_data="order_stub")]
        ]
    )

    await bot.send_photo(
        chat_id=MARKET_GROUP_ID,
        message_thread_id=data["topic_id"],
        photo=data["product_photo"],
        caption=f"🆔 ID: {product_id}\n\n{data['product_text']}",
        reply_markup=kb
    )

    await cleanup(message.chat.id, data["msgs"])
    await state.clear()

@dp.callback_query(F.data == "cancel_add")
async def cancel_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await cleanup(call.message.chat.id, data.get("msgs", []))
    await state.clear()
    await call.answer("Bekor qilindi")

# ================= TOPIC WRITE GUARD (ENG OXIRI) =================
@dp.message(F.chat.id == MARKET_GROUP_ID, F.text)
async def topic_guard(message: Message, state: FSMContext):
    # FSM jarayoni bo‘lsa — tegma
    if await state.get_state():
        return

    # Topic bo‘lmasa — tegma
    if message.message_thread_id is None:
        return

    # Muhokama chat — ruxsat
    if message.message_thread_id == DISCUSSION_TOPIC_ID:
        return

    # Admin — ruxsat
    if await is_admin(message.chat.id, message.from_user.id):
        return

    # Buyruqlarni o‘chirma
    if message.text.startswith("/"):
        return

    # Oddiy user yozdi — o‘chiramiz
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
