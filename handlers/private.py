import time
import asyncio
from aiogram import F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart

from config import ADMIN_CHANNEL_ID, ORDER_TIMEOUT
from storage import ORDERS
from keyboards import size_kb, qty_kb, phone_kb
from utils import update_order_time

async def register_private(dp, bot):

    @dp.message(CommandStart())
    async def start_private(message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) == 1:
            await message.answer("🛒 Buyurtma berish uchun mahsulotdagi tugmani bosing.")
            return

        payload = parts[1]
        if payload.startswith("order_"):
            product_id = payload.replace("order_", "")
            ORDERS[message.from_user.id] = {
                "product_id": product_id,
                "step": "size",
                "last_update": time.time()
            }
            await bot.send_message(message.from_user.id, "👕 O‘lchamni tanlang:", reply_markup=size_kb())

    @dp.callback_query(F.data.startswith("size:"))
    async def choose_size(call: CallbackQuery):
        order = ORDERS.get(call.from_user.id)
        if not order or order["step"] != "size":
            return
        order["size"] = call.data.split(":")[1]
        order["step"] = "qty"
        update_order_time(call.from_user.id)
        await call.message.edit_text("📦 Nechta dona?", reply_markup=qty_kb())

    @dp.callback_query(F.data.startswith("qty:"))
    async def choose_qty(call: CallbackQuery):
        order = ORDERS.get(call.from_user.id)
        if not order or order["step"] != "qty":
            return
        order["quantity"] = call.data.split(":")[1]
        order["step"] = "phone"
        update_order_time(call.from_user.id)
        await call.message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=phone_kb())

    @dp.message(F.contact)
    async def finish_order(message: Message):
        order = ORDERS.pop(message.from_user.id, None)
        if not order:
            return

        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = f"+{phone}"

        await bot.send_message(
            ADMIN_CHANNEL_ID,
            f"🛒 YANGI BUYURTMA\n\n"
            f"🆔 Mahsulot: {order['product_id']}\n"
            f"👕 O‘lcham: {order['size']}\n"
            f"📦 Soni: {order['quantity']}\n"
            f"📞 Tel: {phone}"
        )

        await message.answer("✅ Buyurtma qabul qilindi!", reply_markup=ReplyKeyboardRemove())

    async def order_timeout_watcher():
        while True:
            now = time.time()
            expired = [u for u, d in ORDERS.items() if now - d["last_update"] > ORDER_TIMEOUT]
            for uid in expired:
                ORDERS.pop(uid, None)
                try:
                    await bot.send_message(uid, "⏳ Buyurtma vaqti tugadi.")
                except:
                    pass
            await asyncio.sleep(30)

    
