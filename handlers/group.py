from aiogram import F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import MARKET_GROUP_ID
from storage import ADD_PRODUCT_FLOW
from utils import is_admin


async def register_group(dp, bot, BOT_USERNAME):

    @dp.message(F.text.startswith("/add_product"))
    async def add_product(message: Message):
        if message.chat.id != MARKET_GROUP_ID:
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ Faqat adminlar uchun")
            return

        await message.answer("✅ Buyruq ishladi! Endi davom ettiramiz 🚀")
