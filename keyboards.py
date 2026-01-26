from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add")]
        ]
    )

def size_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("M", callback_data="size:M"),
                InlineKeyboardButton("L", callback_data="size:L"),
                InlineKeyboardButton("XL", callback_data="size:XL"),
            ],
            [InlineKeyboardButton("O‘lcham kerak emas", callback_data="size:none")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="order_cancel")]
        ]
    )

def qty_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("1", callback_data="qty:1"),
                InlineKeyboardButton("2", callback_data="qty:2"),
                InlineKeyboardButton("3", callback_data="qty:3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="qty:4"),
                InlineKeyboardButton("5", callback_data="qty:5"),
            ],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="order_cancel")]
        ]
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
