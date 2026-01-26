import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, BOT_USERNAME
from handlers.group import register_group

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    # GROUP handlerlarni ulaymiz
    await register_group(dp, bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
