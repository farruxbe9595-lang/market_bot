from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("Salom! Bot ishlayapti ✅")

def register_private(dp):
    dp.include_router(router)
