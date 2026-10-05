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


# ==========================================
# ДАННЫЕ
# ==========================================

# Пользователи, которые запустили бота
all_users = set()

# Пользователи + пол
# user_id -> male/female
users = {}

# Кто сейчас ищет собеседника
searching = set()

# Пары
# user_id -> partner_id
partners = {}

# Информация о пользователях
# user_id -> username
usernames = {}


# ==========================================
# АДМИНИСТРАТОР
# ==========================================

ADMIN_ID = 6624599495


# ==========================================
# КЛАВИАТУРЫ
# ==========================================

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


admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="👥 Участники")
        ],
        [
            KeyboardButton(text="🔎 Сейчас ищут"),
            KeyboardButton(text="💬 Сейчас общаются")
        ]
    ],
    resize_keyboard=True
)


# ==========================================
# ПОИСК СОБЕСЕДНИКА
# ==========================================

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


# ==========================================
# START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    # Сохраняем всех, кто запустил бота
    all_users.add(user_id)

    # Сохраняем username
    if message.from_user.username:
        usernames[user_id] = message.from_user.username

    # Если это администратор
    if user_id == ADMIN_ID:

        await message.answer(
            "👑 Панель администратора\n\n"
            "Выбери действие:",
            reply_markup=admin_keyboard
        )
        return

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


# ==========================================
# МУЖЧИНА
# ==========================================

@dp.message(F.text == "👨 Мужчина")
async def choose_male(message: Message):

    user_id = message.from_user.id

    all_users.add(user_id)

    if message.from_user.username:
        usernames[user_id] = message.from_user.username

    users[user_id] = "male"

    await message.answer(
        "✅ Ты указал: мужчина\n\n"
        "🔎 Ищу девушку...",
        reply_markup=chat_keyboard
    )

    await start_search(user_id)


# ==========================================
# ЖЕНЩИНА
# ==========================================

@dp.message(F.text == "👩 Женщина")
async def choose_female(message: Message):

    user_id = message.from_user.id

    all_users.add(user_id)

    if message.from_user.username:
        usernames[user_id] = message.from_user.username

    users[user_id] = "female"

    await message.answer(
        "✅ Ты указала: женщина\n\n"
        "🔎 Ищу мужчину...",
        reply_markup=chat_keyboard
    )

    await start_search(user_id)


# ==========================================
# СЛЕДУЮЩИЙ
# ==========================================

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


# ==========================================
# ЗАВЕРШИТЬ
# ==========================================

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


# ==========================================
# ФУНКЦИЯ СТАТИСТИКИ
# ==========================================

async def send_stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    total_users = len(all_users)

    males = sum(
        1 for gender in users.values()
        if gender == "male"
    )

    females = sum(
        1 for gender in users.values()
        if gender == "female"
    )

    without_gender = total_users - males - females

    searching_now = len(searching)

    chatting_now = len(partners) // 2

    await message.answer(
        "📊 СТАТИСТИКА БОТА\n\n"
        f"👥 Всего участников: {total_users}\n"
        f"👨 Мужчин: {males}\n"
        f"👩 Женщин: {females}\n"
        f"❓ Не выбрали пол: {without_gender}\n\n"
        f"🔎 Сейчас ищут: {searching_now}\n"
        f"💬 Сейчас общаются: {chatting_now}"
    )


# ==========================================
# КНОПКА СТАТИСТИКА
# ==========================================

@dp.message(F.text == "📊 Статистика")
async def stats_button(message: Message):

    await send_stats(message)


# ==========================================
# КОМАНДА /stats
# ==========================================

@dp.message(F.text == "/stats")
async def stats_command(message: Message):

    await send_stats(message)


# ==========================================
# УЧАСТНИКИ
# ==========================================

@dp.message(F.text == "👥 Участники")
async def participants(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    if not all_users:

        await message.answer(
            "👥 Пока никто не запустил бота."
        )
        return

    text = "👥 УЧАСТНИКИ БОТА\n\n"

    # Сортируем ID для удобства
    user_list = sorted(all_users)

    for number, user_id in enumerate(user_list, start=1):

        username = usernames.get(user_id)

        if username:
            name = f"@{username}"
        else:
            name = "без username"

        text += (
            f"{number}. {name}\n"
            f"🆔 ID: {user_id}\n\n"
        )

        # Telegram ограничивает размер сообщения
        if len(text) > 3500:

            await message.answer(text)

            text = "👥 ПРОДОЛЖЕНИЕ\n\n"

    if text.strip() != "👥 ПРОДОЛЖЕНИЕ":

        await message.answer(text)


# ==========================================
# КТО СЕЙЧАС ИЩЕТ
# ==========================================

@dp.message(F.text == "🔎 Сейчас ищут")
async def searching_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    if not searching:

        await message.answer(
            "🔎 Сейчас никто не ищет собеседника."
        )
        return

    text = "🔎 СЕЙЧАС ИЩУТ СОБЕСЕДНИКА\n\n"

    for user_id in searching:

        gender = users.get(user_id, "не указан")

        if gender == "male":
            gender_text = "👨 Мужчина"
        elif gender == "female":
            gender_text = "👩 Женщина"
        else:
            gender_text = "❓ Пол не указан"

        username = usernames.get(user_id)

        if username:
            name = f"@{username}"
        else:
            name = "без username"

        text += (
            f"{name}\n"
            f"🆔 {user_id}\n"
            f"{gender_text}\n\n"
        )

    await message.answer(text)


# ==========================================
# КТО СЕЙЧАС ОБЩАЕТСЯ
# ==========================================

@dp.message(F.text == "💬 Сейчас общаются")
async def chatting_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    if not partners:

        await message.answer(
            "💬 Сейчас никто не общается."
        )
        return

    text = "💬 СЕЙЧАС ОБЩАЮТСЯ\n\n"

    shown = set()
    number = 1

    for user_id, partner_id in partners.items():

        # Чтобы одну пару не показывать два раза
        pair = tuple(sorted([user_id, partner_id]))

        if pair in shown:
            continue

        shown.add(pair)

        username1 = usernames.get(user_id)
        username2 = usernames.get(partner_id)

        name1 = f"@{username1}" if username1 else "без username"
        name2 = f"@{username2}" if username2 else "без username"

        text += (
            f"💬 Пара #{number}\n"
            f"👤 {name1} — {user_id}\n"
            f"👤 {name2} — {partner_id}\n\n"
        )

        number += 1

    await message.answer(text)


# ==========================================
# АНОНИМНЫЙ ЧАТ
# ==========================================

@dp.message()
async def anonymous_chat(message: Message):

    user_id = message.from_user.id

    # Сохраняем пользователя
    all_users.add(user_id)

    if message.from_user.username:
        usernames[user_id] = message.from_user.username

    # Администраторские кнопки
    if user_id == ADMIN_ID:

        admin_buttons = [
            "📊 Статистика",
            "👥 Участники",
            "🔎 Сейчас ищут",
            "💬 Сейчас общаются"
        ]

        if message.text in admin_buttons:
            return

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


# ==========================================
# ЗАПУСК
# ==========================================

async def main():

    print("Bot started!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
