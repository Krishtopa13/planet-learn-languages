import asyncio
import os
import json
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загрузка пользователей
if not os.path.exists("users.json"):
    with open("users.json", "w") as f:
        json.dump({}, f)

def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_users()

# Состояния регистрации
class RegState(StatesGroup):
    name = State()
    goal = State()

# Главное меню
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📚 Учиться"), KeyboardButton(text="✅ Проверить уровень")],
    [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="⚙️ Настройки")],
    [KeyboardButton(text="💎 Премиум"), KeyboardButton(text="❓ Помощь (FAQ)")]
], resize_keyboard=True)

# Команда /start
@dp.message(Command("start"))
async def start_bot(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    today = datetime.date.today().isoformat()

    if user_id not in users:
        users[user_id] = {
            "name": None,
            "goal": None,
            "is_premium": False,
            "points": 0,
            "current_level": "A1",
            "lesson_index": 0,
            "language": "en",
            "voice_enabled": True,
            "voice": "male",
            "accent": "american",
            "start_time": today,
            "last_positive_date": "",
            "daily_positive_enabled": True,
            "registration_time": today,
            "premium_time": None,
            "plan_per_day": None,
            "guest_mode": False
        }
        save_users(users)
        await message.answer(
            "👋 Привет в Planet Learn Languages!\n\nКак тебя зовут?",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚀 Учиться без регистрации")]], resize_keyboard=True)
        )
        await state.set_state(RegState.name)
    else:
        await message.answer("👋 Добро пожаловать обратно в Planet Learn Languages!", reply_markup=main_menu)
    # Структура уроков A1 (шаблон)
    lessons = {
        "A1": {
            "en": [
                {
                    "text": "Lesson 1: Greetings\n- Hello!\n- How are you?\n- I'm fine, thank you!",
                    "test": [
                        ("How do you say 'Привет'?", "hello"),
                        ("How do you answer 'How are you?'?", "I'm fine, thank you")
                    ]
                },
                {
                    "text": "Lesson 2: Numbers\n- One, two, three, four, five.",
                    "test": [
                        ("How do you say 'два'?", "two"),
                        ("How do you say 'пять'?", "five")
                    ]
                }
            ]
        }
    }

    # Позитивные напутствия
    positive_messages_kids = [
        "🌟 Сегодня ты узнаешь что-то новое!",
        "🦄 Учиться — это волшебство!",
        "🐣 Сегодня ты сделаешь маленькое чудо!"
    ]

    positive_messages_adults = [
        "☀️ Маленький шаг каждый день — большая победа.",
        "🚀 Учёба — это свобода. Ты справляешься!",
        "🌍 Новые знания открывают мир для тебя."
    ]

    sent_positive_today = []

    # Отправить позитивное сообщение
    async def send_positive_if_needed(user_id, message):
        today = datetime.date.today().isoformat()
        user = users.get(user_id, {})

        if user.get("daily_positive_enabled", True):
            if user.get("last_positive_date", "") != today:
                pool = positive_messages_kids if user.get("guest_mode", False) else positive_messages_adults
                available = [m for m in pool if m not in sent_positive_today]
                if available:
                    text = random.choice(available)
                    sent_positive_today.append(text)
                    await message.answer(text)
                users[user_id]["last_positive_date"] = today
                save_users(users)

    # Команда Учиться
    @dp.message(F.text == "📚 Учиться")
    async def start_learning(message: types.Message):
        user_id = str(message.from_user.id)
        await send_positive_if_needed(user_id, message)

        user = users.get(user_id, {})
        lang = user.get("language", "en")
        level = user.get("current_level", "A1")
        index = user.get("lesson_index", 0)

        lesson_list = lessons.get(level, {}).get(lang, [])
        if index >= len(lesson_list):
            await message.answer("🎉 Вы прошли все уроки этого уровня!")
            return

        lesson = lesson_list[index]
        await message.answer(lesson["text"])
        await message.answer("✍️ Готов пройти тест? Напиши: Тест")

    # FSM для тестов
    class TestState(StatesGroup):
        waiting_for_answer = State()

    active_tests = {}

    # Запуск теста
    @dp.message(F.text.lower() == "тест")
    async def start_test(message: types.Message, state: FSMContext):
        user_id = str(message.from_user.id)
        user = users.get(user_id, {})
        lang = user.get("language", "en")
        level = user.get("current_level", "A1")
        index = user.get("lesson_index", 0)

        lesson = lessons.get(level, {}).get(lang, [])[index]
        questions = lesson.get("test", [])

        if not questions:
            await message.answer("❌ Нет вопросов.")
            return

        active_tests[user_id] = {
            "questions": questions,
            "current_index": 0,
            "correct": 0
        }

        await state.set_state(TestState.waiting_for_answer)
        await message.answer(f"🧪 Вопрос 1:\n{questions[0][0]}")

    # Приём ответа на тест
    @dp.message(TestState.waiting_for_answer)
    async def answer_test(message: types.Message, state: FSMContext):
        user_id = str(message.from_user.id)
        test = active_tests[user_id]
        answer = message.text.strip().lower()
        correct = test["questions"][test["current_index"]][1].strip().lower()

        if answer == correct:
            test["correct"] += 1
            await message.answer("✅ Верно!")
        else:
            await message.answer(f"❌ Неверно. Правильный ответ: {correct}")

        test["current_index"] += 1
        if test["current_index"] < len(test["questions"]):
            q = test["questions"][test["current_index"]][0]
            await message.answer(f"🧪 Вопрос {test['current_index']+1}:\n{q}")
        else:
            score = test["correct"]
            total = len(test["questions"])
            if score == total:
                users[user_id]["points"] += 10
                users[user_id]["lesson_index"] += 1
                await message.answer(f"🎉 Отлично! Урок пройден! (+10 баллов)")
            else:
                await message.answer(f"📘 Результат: {score}/{total}")
            save_users(users)
            await state.clear()
            del active_tests[user_id]
        # Профиль пользователя
        @dp.message(F.text == "👤 Профиль")
        async def show_profile(message: types.Message):
            user_id = str(message.from_user.id)
            user = users.get(user_id, {})

            name = user.get("name", "Не указано")
            goal = user.get("goal", "Не указано")
            points = user.get("points", 0)
            level = user.get("current_level", "A1")
            premium = "✅ Есть" if user.get("is_premium") else "❌ Нет"
            voice_status = "🔊 Включена" if user.get("voice_enabled", True) else "🔇 Выключена"
            plan = user.get("plan_per_day", "Не задан")

            language_flags = {
                "en": "🇬🇧 English", "es": "🇪🇸 Español", "zh": "🇨🇳 中文", "ar": "🇦🇪 العربية",
                "ru": "🇷🇺 Русский", "uk": "🇺🇦 Українська", "fr": "🇫🇷 Français", "de": "🇩🇪 Deutsch",
                "pt": "🇵🇹 Português", "ja": "🇯🇵 日本語", "ko": "🇰🇷 한국어", "bn": "🇧🇩 বাংলা",
                "hi": "🇮🇳 हिन्दी", "tr": "🇹🇷 Türkçe", "sw": "🌍 Suahili", "ha": "🇳🇬 Hausa",
                "yo": "🇳🇬 Yoruba", "tw": "🇬🇭 Twi", "am": "🇪🇹 አማርኛ", "ln": "🇨🇩 Lingala"
            }

            lang = language_flags.get(user.get("language", "en"), "🇬🇧 English")

            text = (
                f"👤 Имя: {name}\n"
                f"🎯 Цель: {goal}\n"
                f"⭐ Баллы: {points}\n"
                f"💎 Премиум: {premium}\n"
                f"📚 Уровень: {level}\n"
                f"🗓 План на день: {plan}\n"
                f"🌍 Язык интерфейса: {lang}\n"
                f"{voice_status}"
            )
            await message.answer(text)

        # Меню настроек
        @dp.message(F.text == "⚙️ Настройки")
        async def settings_menu(message: types.Message):
            settings_keyboard = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="🌍 Сменить язык"), KeyboardButton(text="🔊 Озвучка: Вкл/Выкл")],
                [KeyboardButton(text="🎯 План на день"), KeyboardButton(text="⬅ Назад в меню")]
            ], resize_keyboard=True)
            await message.answer("⚙️ Настройки бота:", reply_markup=settings_keyboard)

        # Переключение озвучки
        @dp.message(F.text == "🔊 Озвучка: Вкл/Выкл")
        async def toggle_voice(message: types.Message):
            user_id = str(message.from_user.id)
            current = users[user_id].get("voice_enabled", True)
            users[user_id]["voice_enabled"] = not current
            save_users(users)
            status = "🔊 Включена" if users[user_id]["voice_enabled"] else "🔇 Выключена"
            await message.answer(f"Озвучка теперь: {status}", reply_markup=main_menu)

        # Переключение языка
        @dp.message(F.text == "🌍 Сменить язык")
        async def change_language(message: types.Message):
            lang_keyboard = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇪🇸 Español")],
                [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇦 Українська")],
                [KeyboardButton(text="⬅ Назад в меню")]
            ], resize_keyboard=True)
            await message.answer("🌍 Выберите язык интерфейса:", reply_markup=lang_keyboard)

        @dp.message(F.text.regexp("^🇬🇧|🇪🇸|🇷🇺|🇺🇦"))
        async def set_language(message: types.Message):
            user_id = str(message.from_user.id)
            flag = message.text.split()[0]
            lang_map = {
                "🇬🇧": "en", "🇪🇸": "es", "🇷🇺": "ru", "🇺🇦": "uk"
            }
            users[user_id]["language"] = lang_map.get(flag, "en")
            save_users(users)
            await message.answer("✅ Язык сохранён. Для применения перезапустите /start.", reply_markup=main_menu)

        # План на день
        @dp.message(F.text == "🎯 План на день")
        async def set_daily_plan(message: types.Message, state: FSMContext):
            await message.answer("Сколько уроков вы хотите проходить в день?")
            await state.set_state(State(name="plan_setting"))

        @dp.message(State(name="plan_setting"))
        async def save_plan(message: types.Message, state: FSMContext):
            user_id = str(message.from_user.id)
            users[user_id]["plan_per_day"] = message.text.strip()
            save_users(users)
            await message.answer("✅ План установлен!", reply_markup=main_menu)
            await state.clear()
        # Цены премиума по регионам
        price_map = {
            "ha": 1, "yo": 1, "sw": 1, "am": 1, "ln": 1, "bn": 1,
            "uk": 2, "hi": 2, "ar": 2, "tr": 2, "pt": 2,
            "en": 3, "es": 3, "fr": 3, "de": 3, "ja": 3, "ko": 3, "zh": 3, "ru": 2
        }

        ton_wallet = "UQD5Czj7punsmiU_3dIlcb6bSc5GGzPIi_CfreRBERayOUJG"

        # Работа с очередью помощи
        if not os.path.exists("help_queue.json"):
            with open("help_queue.json", "w") as f:
                json.dump([], f)

        def load_help_queue():
            with open("help_queue.json", "r") as f:
                return json.load(f)

        def save_help_queue(queue):
            with open("help_queue.json", "w") as f:
                json.dump(queue, f, indent=2)

        # Показываем меню Премиума
        @dp.message(F.text == "💎 Премиум")
        async def show_premium(message: types.Message):
            user_id = str(message.from_user.id)
            lang = users.get(user_id, {}).get("language", "en")
            price = price_map.get(lang, 3)

            premium_text = (
                f"💎 Премиум-доступ открывает все уроки, тесты, озвучку, голосовую практику и статистику.\n\n"
                f"✅ Стоимость (разовая, навсегда): *{price} TON*\n"
                f"💰 Адрес для оплаты:\n`{ton_wallet}`\n\n"
                f"*Ваш профиль сохраняется 60 дней. После оплаты — продолжите обучение с того же места.*\n\n"
                f"🤝 Цена символическая. Проект создан для развития единого мирового сообщества. Спасибо, что с нами!"
            )

            pay_buttons = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")],
                [InlineKeyboardButton(text="🤝 Помощь в оплате (нет средств)", callback_data="request_help")]
            ])

            await message.answer(premium_text, parse_mode="Markdown", reply_markup=pay_buttons)

        # Подтверждение оплаты
        @dp.callback_query(F.data == "paid")
        async def confirm_paid(callback: types.CallbackQuery):
            user_id = str(callback.from_user.id)
            users[user_id]["is_premium"] = True
            users[user_id]["premium_time"] = datetime.date.today().isoformat()
            save_users(users)
            await callback.message.answer("✅ Спасибо! Премиум активирован навсегда!", reply_markup=main_menu)

        # Запрос помощи в оплате
        @dp.callback_query(F.data == "request_help")
        async def request_help(callback: types.CallbackQuery):
            user_id = str(callback.from_user.id)
            queue = load_help_queue()
            if user_id not in queue:
                queue.append(user_id)
                save_help_queue(queue)
                await callback.message.answer("🤝 Ваша заявка принята. Если кто-то из участников оплатит за вас, вы получите Премиум.")
            else:
                await callback.message.answer("🔄 Ваша заявка уже есть в очереди.")
import aiofiles
import zipfile
import random

# Расчёт общей статистики
def calculate_stats():
    today = datetime.date.today().isoformat()
    total_users = len(users)
    total_premium = sum(1 for u in users.values() if u.get("is_premium"))
    new_today = sum(1 for u in users.values() if u.get("registration_time") == today)
    payments_today = sum(1 for u in users.values() if u.get("premium_time") == today)
    return total_users, total_premium, new_today, payments_today

# Админ ID
ADMIN_ID = 7462557119

# Команда /admin для статистики
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total, premium, new_today, paid_today = calculate_stats()
    await message.answer(
        f"📊 Статистика:\n"
        f"👥 Всего пользователей: {total}\n"
        f"💎 Премиумов: {premium}\n"
        f"➕ Новых сегодня: {new_today}\n"
        f"💰 Оплат сегодня: {paid_today}"
    )

# Ежедневный автоотчёт в 6:15 по Киеву
async def daily_report():
    while True:
        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
        if now.hour == 6 and now.minute == 15:
            total, premium, new_today, paid_today = calculate_stats()
            await bot.send_message(
                ADMIN_ID,
                f"📈 Ежедневный отчёт:\n\n"
                f"👥 Всего: {total}\n"
                f"💎 Премиум: {premium}\n"
                f"➕ Новых: {new_today}\n"
                f"💰 Оплат: {paid_today}"
            )
        await asyncio.sleep(60)

# Автоархивирование пользователей и очереди
async def archive_every_hour():
    while True:
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        users_count = len(users)
        zip_filename = f"backup_{now}_users_{users_count}.zip"

        async with aiofiles.open("users.json", mode='rb') as uf:
            users_data = await uf.read()
        async with aiofiles.open("help_queue.json", mode='rb') as hf:
            help_data = await hf.read()

        with open("users.json", "wb") as f: f.write(users_data)
        with open("help_queue.json", "wb") as f: f.write(help_data)

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            zipf.write("users.json")
            zipf.write("help_queue.json")

        await bot.send_document(ADMIN_ID, types.FSInputFile(zip_filename))
        os.remove(zip_filename)
        await asyncio.sleep(3600)