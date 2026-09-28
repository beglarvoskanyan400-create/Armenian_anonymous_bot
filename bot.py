import asyncio
from aiogram import Bot, Dispatcher

TOKEN = "YOUR_BOT_TOKEN"

dp = Dispatcher()

async def main():
    bot = Bot(token=TOKEN)
    print("Бот запущен!")
    await dp.start_polling(bot)

if _name_ == "_main_":
    asyncio.run(main())
