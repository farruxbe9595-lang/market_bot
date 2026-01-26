from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_cancel_kb() -> InlineKeyboardMarkup:
    """
    Admin uchun: mahsulot qo‘shishni bekor qilish tugmasi
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


def order_button(bot_username: str, product_id: str) -> InlineKeyboardMarkup:
    """
    Mahsulot ostida chiqadigan: Buyurtma berish tugmasi
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Buyurtma berish",
                    url=f"https://t.me/{bot_username}?start=order_{product_id}"
                )
            ]
        ]
    )
