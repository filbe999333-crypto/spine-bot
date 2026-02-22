import asyncio
import logging
import random
import os  # <-- ДОБАВЛЕНО для работы с переменными окружения
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from aiohttp import web  # <-- ДОБАВЛЕНО для веб-сервера (health check)

# --- НАСТРОЙКИ ---
# Берем токен из переменных окружения (так безопаснее!)
TOKEN = os.getenv("BOT_TOKEN", "8432200353:AAEE-YdcvRKTnU0FbAcASbNiFIVdbFR_bC8")  # Ваш токен как запасной вариант
CHANNEL_USERNAME = "@celebrityfunfacts"
CHANNEL_ID = "@celebrityfunfacts"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для хранения активных задач пользователей
user_tasks = {}

# Словарь с интервалами для кнопок
INTERVALS = {
    "1h": 1,
    "5h": 5,
    "10h": 10,
    "15h": 15,
    "20h": 20,
    "24h": 24
}

# Список фраз для напоминаний
REMINDER_PHRASES = [
    "🧘 Выпрями спину!",
    "⚠️ Не горбись!",
    "🦐 Напоминаю, друг, ты прям креветка!",
    "📏 Сядь ровно, осанка — это важно!",
    "🏛️ Расправь плечи, как греческая колонна!",
    "💪 Держи спину, чемпион!",
    "🪑 Отлипни от стола, выпрямись!",
    "🎗️ Не сутулься, побереги позвоночник!"
]

# Функция проверки подписки
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except Exception as e:
        print(f"Ошибка проверки подписки для {user_id}: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    is_subscribed = await check_subscription(user_id)

    if is_subscribed:
        await show_timer_menu(message)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/celebrityfunfacts")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
        ])
        await message.answer(
            f"Привет, {user_name}!\n\n"
            f"Для использования бота нужно подписаться на наш канал: {CHANNEL_USERNAME}\n\n"
            f"👉 После подписки нажми кнопку 'Я подписался'.",
            reply_markup=keyboard
        )

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_sub_check(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)

    if is_subscribed:
        await callback.message.edit_text("✅ Спасибо! Подписка подтверждена. Выбирай интервал:")
        await show_timer_menu(callback.message)
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

async def show_timer_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час", callback_data="set_1h"),
         InlineKeyboardButton(text="5 часов", callback_data="set_5h")],
        [InlineKeyboardButton(text="10 часов", callback_data="set_10h"),
         InlineKeyboardButton(text="15 часов", callback_data="set_15h")],
        [InlineKeyboardButton(text="20 часов", callback_data="set_20h"),
         InlineKeyboardButton(text="24 часа", callback_data="set_24h")],
        [InlineKeyboardButton(text="❌ Выключить напоминания", callback_data="stop_reminders")]
    ])
    await message.answer("⏰ Напомнить мне выпрямить спину каждые:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("set_"))
async def set_reminder(callback: CallbackQuery):
    user_id = callback.from_user.id
    interval_key = callback.data
    interval_hours = INTERVALS[interval_key.replace("set_", "")]

    next_time = datetime.now() + timedelta(hours=interval_hours)

    user_tasks[user_id] = {
        "chat_id": callback.message.chat.id,
        "next_time": next_time,
        "interval_hours": interval_hours
    }

    await callback.message.edit_text(
        f"✅ Напоминание установлено!\n"
        f"Я буду напоминать тебе каждые {interval_hours} час(ов).\n"
        f"Первое напоминание придет примерно в {next_time.strftime('%H:%M %d.%m')}."
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stop_reminders")
async def stop_reminders(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in user_tasks:
        del user_tasks[user_id]
        await callback.message.edit_text("🔕 Напоминания отключены. Чтобы включить заново, нажми /start")
    else:
        await callback.message.edit_text("🤷 У тебя не было активных напоминаний.")
    await callback.answer()

# --- Фоновая задача для рассылки напоминаний ---
async def reminder_scheduler():
    while True:
        now = datetime.now()
        to_remove = []

        for user_id, task_info in user_tasks.items():
            if now >= task_info["next_time"]:
                try:
                    phrase = random.choice(REMINDER_PHRASES)
                    await bot.send_message(chat_id=task_info["chat_id"], text=phrase)

                    new_next_time = now + timedelta(hours=task_info["interval_hours"])
                    user_tasks[user_id]["next_time"] = new_next_time
                    print(f"Отправлено напоминание пользователю {user_id}. Следующее в {new_next_time}")

                except Exception as e:
                    print(f"Ошибка отправки пользователю {user_id}: {e}. Удаляем из списка.")
                    to_remove.append(user_id)

        for user_id in to_remove:
            if user_id in user_tasks:
                del user_tasks[user_id]

        await asyncio.sleep(30)

# --- НОВОЕ: Веб-сервер для Health Check (чтобы Render не выключал бота) ---
async def handle_health(request):
    """Простой ответ, что бот жив"""
    return web.Response(text="OK")

async def run_web_server():
    """Запускает веб-сервер для health check"""
    app = web.Application()
    app.router.add_get("/health", handle_health)  # Render будет проверять этот адрес
    
    port = int(os.getenv("PORT", 10000))  # Render сам дает порт через переменную PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер для health check запущен на порту {port}")
    return runner

# --- ИСПРАВЛЕНО: Главная функция запуска ---
async def main():
    # Запускаем веб-сервер для health check (нужно Render)
    web_runner = await run_web_server()
    
    # Запускаем фоновую задачу планировщика
    asyncio.create_task(reminder_scheduler())
    
    # Запускаем бота (поллинг)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
