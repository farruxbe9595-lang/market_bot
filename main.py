from aiogram import Bot, Dispatcher
import asyncio
from config import BOT_TOKEN
from handlers.group import register_group
from handlers.private import register_private

BOT_USERNAME = "Buyurtma9020_bot"

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    await register_group(dp, bot, BOT_USERNAME)
    await register_private(dp, bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
