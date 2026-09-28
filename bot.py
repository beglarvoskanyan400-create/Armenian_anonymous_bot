import asyncio
import os
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


TOKEN = os.getenv("TOKEN")

# Твой Telegram ID
ADMIN_ID = 6624599495

dp = Dispatcher()

# Пользователи: user_id -> пол
users = {}

# Кто сейчас ищет собеседника
searching = set()

# Пары: user_id -> user_id
partners = {}


# =========================
# Загрузка пользователей
# =========================

try:
    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)

    # JSON сохраняет ключи как строки
    users = {int(user_id): gender for user_id, gender in users.items()}

except (FileNotFoundError, json.JSONDecodeError):
    users = {}


def save_users():
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)


def gender_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👨 Мужчина"),
                KeyboardButton(text="👩 Женщина")
            ]
        ],
        resize_keyboard=True
    )


def chat_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="⏭ Следующий"),
                KeyboardButton(text="🛑 Завершить")
            ]
        ],
        resize_keyboard=True
    )


# =========================
# /start
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    # Добавляем нового пользователя
    if user_id not in users:
        users[user_id] = None
        save_users()

    await message.answer(
        "👋 Добро пожаловать в анонимный чат!\n\n"
        "Сначала выбери свой пол:",
        reply_markup=gender_keyboard()
    )


# =========================
# Выбор пола
# =========================

@dp.message(F.text.in_({"👨 Мужчина", "👩 Женщина"}))
async def choose_gender(message: Message):
    user_id = message.from_user.id

    if message.text == "👨 Мужчина":
        users[user_id] = "male"
    else:
        users[user_id] = "female"

    save_users()

    await message.answer(
        "✅ Пол выбран.\n\n"
        "🔎 Ищу собеседника...",
        reply_markup=chat_keyboard()
    )

    await find_partner(message)


# =========================
# Поиск собеседника
# =========================

async def find_partner(message: Message):
    user_id = message.from_user.id

    if user_id in partners:
        return

    for other_id in list(searching):
        if other_id == user_id:
            continue

        if other_id not in users:
            continue

        searching.discard(other_id)
        searching.discard(user_id)

        partners[user_id] = other_id
        partners[other_id] = user_id

        await message.answer(
            "🎉 Собеседник найден!\n\n"
            "Можете начинать общение.",
            reply_markup=chat_keyboard()
        )

        try:
            await message.bot.send_message(
                other_id,
                "🎉 Собеседник найден!\n\n"
                "Можете начинать общение.",
                reply_markup=chat_keyboard()
            )
        except Exception:
            pass

        return

    searching.add(user_id)


# =========================
# Следующий собеседник
# =========================

@dp.message(F.text == "⏭ Следующий")
async def next_chat(message: Message):
    user_id = message.from_user.id

    if user_id in partners:
        other_id = partners.pop(user_id)
        partners.pop(other_id, None)

        try:
            await message.bot.send_message(
                other_id,
                "👋 Собеседник завершил разговор.\n\n"
                "🔎 Ищу нового собеседника..."
            )
            searching.add(other_id)
        except Exception:
            pass

    searching.discard(user_id)

    await message.answer("🔎 Ищу нового собеседника...")
    await find_partner(message)


# =========================
# Завершить чат
# =========================

@dp.message(F.text == "🛑 Завершить")
async def end_chat(message: Message):
    user_id = message.from_user.id

    searching.discard(user_id)

    if user_id in partners:
        other_id = partners.pop(user_id)
        partners.pop(other_id, None)

        try:
            await message.bot.send_message(
                other_id,
                "🛑 Собеседник завершил разговор."
            )
        except Exception:
            pass

    await message.answer(
        "Разговор завершён.\n\n"
        "Чтобы начать новый поиск, нажми /start"
    )


# =========================
# Статистика
# =========================

@dp.message(F.text == "/stats")
async def stats(message: Message):
    # Только для владельца бота
    if message.from_user.id != ADMIN_ID:
        return

    total_users = len(users)
    searching_users = len(searching)
    active_chats = len(partners) // 2

    await message.answer(
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🔎 Ищут собеседника: {searching_users}\n"
        f"💬 Сейчас в чатах: {active_chats}"
    )


# =========================
# Анонимные сообщения
# =========================

@dp.message()
async def anonymous_message(message: Message):
    user_id = message.from_user.id

    if user_id not in partners:
        await message.answer(
            "🔎 Сейчас ты не в чате.\n"
            "Нажми /start, чтобы начать."
        )
        return

    other_id = partners[user_id]

    try:
        await message.bot.send_message(
            other_id,
            message.text
        )
    except Exception:
        await message.answer(
            "⚠️ Не удалось отправить сообщение."
        )


# =========================
# Запуск
# =========================

async def main():
    if not TOKEN:
        raise RuntimeError("TOKEN не найден")

    bot = Bot(token=TOKEN)

    print("Бот запущен!")

    await dp.start_polling(bot)


asyncio.run(main())
