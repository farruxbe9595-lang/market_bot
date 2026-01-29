from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_add")]
        ]
    )
