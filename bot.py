import asyncio
import os
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ================= WINDOWS =================
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MARKET_GROUP_ID = -1003618675735
DISCUSSION_TOPIC_ID = 1

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================= STATES =================
class AddProductState(StatesGroup):
    photo = State()
    text = State()
    product_id = State()

# ================= KEYBOARD =================
def cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_admin")]
        ]
    )

# ================= ADMIN CHECK =================
async def is_admin(chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

# ================= ADD PRODUCT =================
@dp.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    if message.chat.id != MARKET_GROUP_ID:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    if message.message_thread_id is None:
        await message.answer("❗ Faqat topic ichida ishlaydi")
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

# ================= PHOTO =================
@dp.message(
    StateFilter(AddProductState.photo),
    F.photo | (F.document & F.document.mime_type.startswith("image/"))
)
async def add_product_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    msgs = data.get("msgs", [])
    msgs.append(message.message_id)

    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    msg = await message.answer(
        "📝 Tavsifni yuboring:",
        reply_markup=cancel_kb()
    )

    await state.update_data(
        product_photo=file_id,
        msgs=msgs + [msg.message_id]
    )
    await state.set_state(AddProductState.text)

# ================= TEXT =================
@dp.message(StateFilter(AddProductState.text), F.text)
async def add_product_text(message: Message, state: FSMContext):
    data = await state.get_data()
    msgs = data["msgs"] + [message.message_id]

    msg = await message.answer(
        "🆔 Mahsulot ID yozing:",
        reply_markup=cancel_kb()
    )

    await state.update_data(
        product_text=message.text,
        msgs=msgs + [msg.message_id]
    )
    await state.set_state(AddProductState.product_id)

# ================= PUBLISH =================
@dp.message(StateFilter(AddProductState.product_id), F.text)
async def add_product_publish(message: Message, state: FSMContext):
    data = await state.get_data()

    await bot.send_photo(
        chat_id=MARKET_GROUP_ID,
        message_thread_id=data["topic_id"],
        photo=data["product_photo"],
        caption=f"🆔 ID: {message.text}\n\n{data['product_text']}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Buyurtma berish", callback_data="noop")]
            ]
        )
    )

    for mid in data["msgs"]:
        try:
            await bot.delete_message(message.chat.id, mid)
        except:
            pass

    await state.clear()

# ================= CANCEL =================
@dp.callback_query(F.data == "cancel_admin")
async def cancel_admin(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for mid in data.get("msgs", []):
        try:
            await bot.delete_message(call.message.chat.id, mid)
        except:
            pass
    await state.clear()
    await call.answer("Bekor qilindi")

@dp.message(F.chat.id == MARKET_GROUP_ID, F.text)
async def topic_guard(message: Message, state: FSMContext):
    # FSM ishlayapti — tegma
    if await state.get_state() is not None:
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

    try:
        await message.delete()
    except:
        pass


# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
