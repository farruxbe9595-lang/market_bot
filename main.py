import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.group import router as group_router
from handlers.private import router as private_router

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(group_router)
    dp.include_router(private_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
