from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_cancel_kb() -> InlineKeyboardMarkup:
    """
    Admin mahsulot qo‘shish jarayonini bekor qilish uchun tugma
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_add"
                )
            ]
        ]
    )
