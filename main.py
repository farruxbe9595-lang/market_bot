import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.group import register_group
from handlers.private import register_private

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    me = await bot.get_me()
    BOT_USERNAME = me.username

    await register_group(dp, bot, BOT_USERNAME)
    await register_private(dp, bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
