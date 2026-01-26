from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

from storage import ORDERS
from config import ADMIN_CHANNEL_ID

router = Router()

@router.message(CommandStart())
async def start_private(message: Message):
    if message.text.startswith("/start order_"):
        product_id = message.text.split("order_")[1]

        ORDERS[message.from_user.id] = {
            "product_id": product_id,
            "step": "size"
        }

        await message.answer(
            "👕 O‘lchamni tanlang:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton("M", callback_data="size:M"),
                        InlineKeyboardButton("L", callback_data="size:L"),
                        InlineKeyboardButton("XL", callback_data="size:XL")
                    ],
                    [
                        InlineKeyboardButton("📦 Kerak emas", callback_data="size:none")
                    ]
                ]
            )
        )
    else:
        await message.answer("🛒 Buyurtma berish uchun mahsulotdagi tugmani bosing.")

@router.callback_query(F.data.startswith("size:"))
async def choose_size(call):
    order = ORDERS.get(call.from_user.id)
    if not order:
        return

    order["size"] = call.data.split(":")[1]
    order["step"] = "qty"

    await call.message.edit_text(
        "📦 Nechta dona?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("1", callback_data="qty:1"),
                    InlineKeyboardButton("2", callback_data="qty:2"),
                    InlineKeyboardButton("3", callback_data="qty:3"),
                ]
            ]
        )
    )

@router.callback_query(F.data.startswith("qty:"))
async def choose_qty(call):
    order = ORDERS.get(call.from_user.id)
    if not order:
        return

    order["quantity"] = call.data.split(":")[1]
    order["step"] = "phone"

    await call.message.answer(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

@router.message(F.contact)
async def finish_order(message: Message):
    order = ORDERS.pop(message.from_user.id, None)
    if not order:
        return

    phone = message.contact.phone_number

    await message.bot.send_message(
        ADMIN_CHANNEL_ID,
        f"🛒 YANGI BUYURTMA\n\n"
        f"🆔 Mahsulot: {order['product_id']}\n"
        f"👕 O‘lcham: {order['size']}\n"
        f"📦 Soni: {order['quantity']}\n"
        f"📞 Tel: {phone}"
    )

    await message.answer("✅ Buyurtma qabul qilindi!", reply_markup=ReplyKeyboardRemove())
