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

# Все пользователи, которые запускали бота
all_users = set()

# Пользователь -> пол
# male / female
users = {}

# Пользователи, которые ищут собеседника
searching = set()

# Пары
# user_id -> partner_id
partners = {}

# Username пользователей
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


# Админская клавиатура
# Здесь есть и админские функции,
# и управление обычным чатом.

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="👥 Участники")
        ],
        [
            KeyboardButton(text="🔎 Сейчас ищут"),
            KeyboardButton(text="💬 Сейчас общаются")
        ],
        [
            KeyboardButton(text="⏭ Следующий"),
            KeyboardButton(text="🛑 Завершить")
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

    # Клавиатура для админа
    keyboard_user = (
        admin_keyboard
        if user_id == ADMIN_ID
        else chat_keyboard
    )

    keyboard_partner = (
        admin_keyboard
        if partner_id == ADMIN_ID
        else chat_keyboard
    )

    await bot.send_message(
        user_id,
        "🎉 Собеседник найден!\n\n"
        "Можете начинать общение.",
        reply_markup=keyboard_user
    )

    await bot.send_message(
        partner_id,
        "🎉 Собеседник найден!\n\n"
        "Можете начинать общение.",
        reply_markup=keyboard_partner
    )


# ==========================================
# START
# ==========================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    # Записываем пользователя
    all_users.add(user_id)

    # Сохраняем username
    if message.from_user.username:
        usernames[user_id] = message.from_user.username

    # ======================================
    # АДМИНИСТРАТОР
    # ======================================

    if user_id == ADMIN_ID:

        await message.answer(
            "👑 Админская панель\n\n"
            "Ты также можешь пользоваться ботом "
            "как обычный участник.\n\n"
            "Сначала выбери свой пол:",
            reply_markup=gender_keyboard
        )

        await message.answer(
            "📊 Админские функции доступны после выбора пола.",
            reply_markup=admin_keyboard
        )

        return

    # ======================================
    # ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ
    # ======================================

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

    keyboard = (
        admin_keyboard
        if user_id == ADMIN_ID
        else chat_keyboard
    )

    await message.answer(
        "✅ Ты указал: мужчина\n\n"
        "🔎 Ищу девушку...",
        reply_markup=keyboard
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

    keyboard = (
        admin_keyboard
        if user_id == ADMIN_ID
        else chat_keyboard
    )

    await message.answer(
        "✅ Ты указала: женщина\n\n"
        "🔎 Ищу мужчину...",
        reply_markup=keyboard
    )

    await start_search(user_id)


# ==========================================
# СТАТИСТИКА
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
# /stats
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

    for number, user_id in enumerate(
        sorted(all_users),
        start=1
    ):

        username = usernames.get(user_id)

        if username:
            name = f"@{username}"
        else:
            name = "без username"

        if user_id in users:
            gender = users[user_id]

            if gender == "male":
                gender_text = "👨 Мужчина"
            else:
                gender_text = "👩 Женщина"
        else:
            gender_text = "❓ Пол не указан"

        text += (
            f"{number}. {name}\n"
            f"🆔 ID: {user_id}\n"
            f"{gender_text}\n\n"
        )

        # Не превышаем лимит Telegram
        if len(text) > 3500:

            await message.answer(text)

            text = "👥 ПРОДОЛЖЕНИЕ\n\n"

    if text.strip() != "👥 ПРОДОЛЖЕНИЕ":

        await message.answer(text)


# ==========================================
# СЕЙЧАС ИЩУТ
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

    text = "🔎 СЕЙЧАС ИЩУТ\n\n"

    for user_id in searching:

        gender = users.get(user_id)

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
# СЕЙЧАС ОБЩАЮТСЯ
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

        pair = tuple(
            sorted([user_id, partner_id])
        )

        if pair in shown:
            continue

        shown.add(pair)

        username1 = usernames.get(user_id)
        username2 = usernames.get(partner_id)

        name1 = (
            f"@{username1}"
            if username1
            else "без username"
        )

        name2 = (
            f"@{username2}"
            if username2
            else "без username"
        )

        text += (
            f"💬 Пара #{number}\n"
            f"👤 {name1} — {user_id}\n"
            f"👤 {name2} — {partner_id}\n\n"
        )

        number += 1

    await message.answer(text)


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

                partner_keyboard = (
                    admin_keyboard
                    if old_partner == ADMIN_ID
                    else chat_keyboard
                )

                await bot.send_message(
                    old_partner,
                    "👋 Собеседник завершил разговор.",
                    reply_markup=partner_keyboard
                )

            except Exception:
                pass

    searching.discard(user_id)

    keyboard = (
        admin_keyboard
        if user_id == ADMIN_ID
        else chat_keyboard
    )

    await message.answer(
        "🔎 Ищу нового собеседника...",
        reply_markup=keyboard
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

    keyboard = (
        admin_keyboard
        if user_id == ADMIN_ID
        else chat_keyboard
    )

    if partner_id:

        partners.pop(user_id, None)
        partners.pop(partner_id, None)

        try:

            partner_keyboard = (
                admin_keyboard
                if partner_id == ADMIN_ID
                else chat_keyboard
            )

            await bot.send_message(
                partner_id,
                "👋 Собеседник завершил разговор.",
                reply_markup=partner_keyboard
            )

        except Exception:
            pass

        await message.answer(
            "🛑 Чат завершён.",
            reply_markup=keyboard
        )

    else:

        await message.answer(
            "🛑 Поиск остановлен.",
            reply_markup=keyboard
        )


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

    # Админские кнопки обрабатываются
    # отдельными handlers выше.
    if user_id == ADMIN_ID:

        admin_buttons = [
            "📊 Статистика",
            "👥 Участники",
            "🔎 Сейчас ищут",
            "💬 Сейчас общаются"
        ]

        if message.text in admin_buttons:
            return

    # Если пользователь не выбрал пол
    if user_id not in users:

        await message.answer(
            "Сначала выбери свой пол:",
            reply_markup=gender_keyboard
        )

        return

    # Пока ищет
    if user_id in searching:

        await message.answer(
            "🔎 Я пока ищу тебе собеседника..."
        )

        return

    # Нет партнёра
    if user_id not in partners:

        keyboard = (
            admin_keyboard
            if user_id == ADMIN_ID
            else chat_keyboard
        )

        await message.answer(
            "У тебя сейчас нет собеседника.\n"
            "Нажми ⏭ Следующий.",
            reply_markup=keyboard
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

        keyboard = (
            admin_keyboard
            if user_id == ADMIN_ID
            else chat_keyboard
        )

        await message.answer(
            "❌ Не удалось отправить сообщение.\n"
            "Нажми ⏭ Следующий.",
            reply_markup=keyboard
        )


# ==========================================
# ЗАПУСК
# ==========================================

async def main():

    print("Bot started!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
