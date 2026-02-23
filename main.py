import logging
import random
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN", "8432200353:AAEE-YdcvRKTnU0FbAcASbNiFIVdbFR_bC8")
CHANNEL_USERNAME = "@celebrityfunfacts"
CHANNEL_ID = "@celebrityfunfacts"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Хранилище активных напоминаний: {user_id: {"chat_id": id, "next_time": datetime, "interval_hours": int}}
user_tasks = {}

INTERVALS = {
    "1h": 1,
    "5h": 5,
    "10h": 10,
    "15h": 15,
    "20h": 20,
    "24h": 24
}

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

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member['status'] in ['member', 'administrator', 'creator']
    except:
        return False

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if await check_subscription(user_id):
        await show_timer_menu(message)
    else:
        keyboard = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/celebrityfunfacts"),
            InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")
        )
        await message.answer(
            f"Привет, {message.from_user.first_name}!\n\nПодпишись на {CHANNEL_USERNAME} и нажми кнопку.",
            reply_markup=keyboard
        )

@dp.callback_query_handler(lambda c: c.data == 'check_sub')
async def process_sub_check(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text("✅ Спасибо! Выбирай интервал:")
        await show_timer_menu(callback.message)
    else:
        await callback.answer("❌ Ты не подписан!", show_alert=True)

async def show_timer_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(text="1 час", callback_data="set_1h"),
        InlineKeyboardButton(text="5 часов", callback_data="set_5h"),
        InlineKeyboardButton(text="10 часов", callback_data="set_10h"),
        InlineKeyboardButton(text="15 часов", callback_data="set_15h"),
        InlineKeyboardButton(text="20 часов", callback_data="set_20h"),
        InlineKeyboardButton(text="24 часа", callback_data="set_24h"),
        InlineKeyboardButton(text="❌ Выключить", callback_data="stop_reminders")
    )
    await message.answer("⏰ Напоминать каждые:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('set_'))
async def set_reminder(call: types.CallbackQuery):
    user_id = call.from_user.id
    hours = INTERVALS[call.data.replace("set_", "")]
    next_time = datetime.now() + timedelta(hours=hours)
    msk_time = next_time + timedelta(hours=3)

    user_tasks[user_id] = {
        "chat_id": call.message.chat.id,
        "next_time": next_time,
        "interval_hours": hours
    }

    await call.message.edit_text(
        f"✅ Напоминание каждые {hours} ч.\n"
        f"🇷🇺 Первое по Москве: {msk_time.strftime('%H:%M %d.%m')}"
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == 'stop_reminders')
async def stop_reminders(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in user_tasks:
        del user_tasks[user_id]
        text = "🔕 Напоминания отключены"
    else:
        text = "🤷 Нет активных напоминаний"
    await call.message.edit_text(text)
    await call.answer()

# --- ПЛАНИРОВЩИК РАССЫЛКИ (работает в фоне) ---
async def reminder_scheduler():
    print("✅ Планировщик запущен и работает!")
    while True:
        now = datetime.now()
        to_remove = []
        for uid, task in user_tasks.items():
            if now >= task["next_time"]:
                try:
                    phrase = random.choice(REMINDER_PHRASES)
                    await bot.send_message(chat_id=task["chat_id"], text=phrase)
                    task["next_time"] = now + timedelta(hours=task["interval_hours"])
                    print(f"✓ Напоминание отправлено {uid}")
                except:
                    to_remove.append(uid)
        for uid in to_remove:
            user_tasks.pop(uid, None)
        await asyncio.sleep(30)

# --- HEALTH CHECK (чтобы Render не усыплял) ---
async def handle_health(request):
    return web.Response(text="OK")

async def run_health_server():
    app = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000))).start()
    print("🌐 Health check сервер запущен")

# --- ТОЧКА ВХОДА ---
async def main():
    await run_health_server()
    asyncio.create_task(reminder_scheduler())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
