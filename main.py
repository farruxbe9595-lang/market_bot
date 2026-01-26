import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.group import register_group
from handlers.private import register_private, order_timeout_watcher

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    await register_group(dp)
    await register_private(dp, bot)

    # ✅ TO‘G‘RI: asyncio orqali task yaratish
    asyncio.create_task(order_timeout_watcher())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
