import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, BOT_USERNAME
from handlers.group import register_group
from handlers.private import register_private


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # handlerlarni ulash (await YO‘Q)
    register_private(dp)
    register_group(dp, bot, BOT_USERNAME)

    print("✅ Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
