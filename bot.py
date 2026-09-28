import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN not found")


bot = Bot(token=TOKEN)
dp = Dispatcher()


# Пользователи: user_id -> пол
users = {}

# Кто сейчас ищет собеседника
searching = set()

# Пары: user_id -> partner_id
partners = {}


# ID администратора
ADMIN_ID = 6624599495


# =========================
# КЛАВИАТУРЫ
# =========================

gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👨 Мужчина"),
            KeyboardButton(text="👩 Женщина")
        ]
    ],
    resize_keyboard=True
)


chat_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⏭ Следующий"),
            KeyboardButton(text="🛑 Завершить")
        ]
    ],
    resize_keyboard=True
)


# =========================
# ПОИСК СОБЕСЕДНИКА
# =========================

def find_partner(user_id):

    my_gender = users.get(user_id)

    if not my_gender:
        return None

    for other_id in list(searching):

        if other_id == user_id:
            continue

        other_gender = users.get(other_id)

        if not other_gender:
            continue

        # Только противоположный пол
        if my_gender != other_gender:
            return other_id

    return None


async def start_search(user_id):

    if user_id in partners:
        return

    searching.add(user_id)

    partner_id = find_partner(user_id)

    if partner_id is None:
        return

    searching.discard(user_id)
    searching.discard(partner_id)

    partners[user_id] = partner_id
    partners[partner_id] = user_id

    await bot.send_message(
        user_id,
        "🎉 Собеседник найден!\n\n"
        "Можете начинать общение.",
        reply_markup=chat_keyboard
    )

    await bot.send_message(
        partner_id,
        "🎉 Собеседник найден!\n\n"
        "Можете начинать общение.",
        reply_markup=chat_keyboard
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    if user_id in partners:
        await message.answer(
            "Ты уже общаешься с собеседником.",
            reply_markup=chat_keyboard
        )
        return

    await message.answer(
        "👋 Добро пожаловать в анонимный чат!\n\n"
        "Выбери свой пол:",
        reply_markup=gender_keyboard
    )


# =========================
# МУЖЧИНА
# =========================

@dp.message(F.text == "👨 Мужчина")
async def choose_male(message: Message):

    user_id = message.from_user.id

    users[user_id] = "male"

    await message.answer(
        "✅ Ты указал: мужчина\n\n"
        "🔎 Ищу девушку...",
        reply_markup=chat_keyboard
    )

    await start_search(user_id)


# =========================
# ЖЕНЩИНА
# =========================

@dp.message(F.text == "👩 Женщина")
async def choose_female(message: Message):

    user_id = message.from_user.id

    users[user_id] = "female"

    await message.answer(
        "✅ Ты указала: женщина\n\n"
        "🔎 Ищу мужчину...",
        reply_markup=chat_keyboard
    )

    await start_search(user_id)


# =========================
# СЛЕДУЮЩИЙ
# =========================

@dp.message(F.text == "⏭ Следующий")
async def next_partner(message: Message):

    user_id = message.from_user.id

    if user_id in partners:

        old_partner = partners.get(user_id)

        partners.pop(user_id, None)

        if old_partner:
            partners.pop(old_partner, None)

            try:
                await bot.send_message(
                    old_partner,
                    "👋 Собеседник завершил разговор.",
                    reply_markup=chat_keyboard
                )
            except Exception:
                pass

    searching.discard(user_id)

    await message.answer(
        "🔎 Ищу нового собеседника...",
        reply_markup=chat_keyboard
    )

    await start_search(user_id)


# =========================
# ЗАВЕРШИТЬ
# =========================

@dp.message(F.text == "🛑 Завершить")
async def stop_chat(message: Message):

    user_id = message.from_user.id

    searching.discard(user_id)

    partner_id = partners.get(user_id)

    if partner_id:

        partners.pop(user_id, None)
        partners.pop(partner_id, None)

        try:
            await bot.send_message(
                partner_id,
                "👋 Собеседник завершил разговор.",
                reply_markup=chat_keyboard
            )
        except Exception:
            pass

        await message.answer(
            "🛑 Чат завершён.",
            reply_markup=chat_keyboard
        )

    else:

        await message.answer(
            "🛑 Поиск остановлен.",
            reply_markup=chat_keyboard
        )


# =========================
# СТАТИСТИКА
# =========================

@dp.message(F.text == "/stats")
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    total_users = len(users)

    males = sum(
        1 for gender in users.values()
        if gender == "male"
    )

    females = sum(
        1 for gender in users.values()
        if gender == "female"
    )

    searching_now = len(searching)

    chatting_now = len(partners) // 2

    await message.answer(
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"👨 Мужчин: {males}\n"
        f"👩 Женщин: {females}\n"
        f"🔎 Ищут собеседника: {searching_now}\n"
        f"💬 Сейчас общаются: {chatting_now}"
    )


# =========================
# АНОНИМНЫЙ ЧАТ
# =========================

@dp.message()
async def anonymous_chat(message: Message):

    user_id = message.from_user.id

    if user_id not in users:

        await message.answer(
            "Сначала выбери свой пол:",
            reply_markup=gender_keyboard
        )

        return

    if user_id in searching:

        await message.answer(
            "🔎 Я пока ищу тебе собеседника..."
        )

        return

    if user_id not in partners:

        await message.answer(
            "У тебя сейчас нет собеседника.\n"
            "Нажми ⏭ Следующий.",
            reply_markup=chat_keyboard
        )

        return

    partner_id = partners.get(user_id)

    if not partner_id:
        return

    try:

        await message.copy_to(partner_id)

    except Exception:

        partners.pop(user_id, None)
        partners.pop(partner_id, None)

        await message.answer(
            "❌ Не удалось отправить сообщение.\n"
            "Нажми ⏭ Следующий.",
            reply_markup=chat_keyboard
        )


# =========================
# ЗАПУСК
# =========================

async def main():

    print("Bot started!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
