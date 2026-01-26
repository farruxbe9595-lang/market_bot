import time
from aiogram import Bot
from config import ORDER_TIMEOUT
from storage import ORDERS

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    admins = await bot.get_chat_administrators(chat_id)
    return any(a.user.id == user_id for a in admins)

def update_order_time(user_id: int):
    if user_id in ORDERS:
        ORDERS[user_id]["last_update"] = time.time()
