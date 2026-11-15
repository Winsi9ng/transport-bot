import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    WebAppInfo, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    LabeledPrice
)

# 1. Встав сюди свій токен від @BotFather
TOKEN = "9107537529:AAF1UBLdvxjQr5Yg-Lx0ZUser_LUmZuQNbs"

# 2. Посилання на твій сайт-квиток на GitHub Pages
WEB_APP_URL = "https://winsi9ng.github.io/transport-app/"

# 3. Встав сюди свій числовий Telegram ID (дізнайся у @userinfobot), щоб бути адміном
ADMIN_ID = 2142667662  

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Проста база даних у пам'яті
users_db = {
    ADMIN_ID: {"subscription_end": datetime.now() + timedelta(days=9999), "tickets": 999}
}

# Прайс-лист послуг у зірках Telegram (XTR)
PRICES = {
    "1_ticket": {"title": "1 квиток", "price": 5, "type": "ticket"},
    "sub_day": {"title": "Доступ на 1 день", "price": 15, "type": "sub", "days": 1},
    "sub_week": {"title": "Доступ на 1 тиждень", "price": 35, "type": "sub", "days": 7},
    "sub_month": {"title": "Доступ на 1 місяць", "price": 50, "type": "sub", "days": 30},
    "sub_halfyear": {"title": "Доступ на пів року", "price": 150, "type": "sub", "days": 180},
    "sub_year": {"title": "Доступ на 1 рік", "price": 250, "type": "sub", "days": 365},
    "sub_forever": {"title": "Доступ назавжди", "price": 400, "type": "sub", "days": 99999},
}

def check_access(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    user = users_db.get(user_id)
    if not user:
        return False
    if user.get("subscription_end") and user["subscription_end"] > datetime.now():
        return True
    if user.get("tickets", 0) > 0:
        return True
    return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_db:
        users_db[user_id] = {"subscription_end": None, "tickets": 0}

    user = users_db[user_id]
    
    status_text = "❌ У вас немає активного доступу."
    if user_id == ADMIN_ID:
        status_text = "👑 Ви адміністратор цього бота."
    elif user["subscription_end"] and user["subscription_end"] > datetime.now():
        date_str = user["subscription_end"].strftime("%d.%m.%Y о %H:%M")
        status_text = f"✅ Ваша підписка активна до: *{date_str}*"
    elif user["tickets"] > 0:
        status_text = f"🎫 Доступно квитків: *{user['tickets']}*"

    keyboard_buttons = [
        [InlineKeyboardButton(text="🎫 Купити 1 квиток (5 ⭐️)", callback_data="buy_1_ticket")],
        [InlineKeyboardButton(text="📅 Доступ на 1 день (15 ⭐️)", callback_data="buy_sub_day")],
        [InlineKeyboardButton(text="🗓 Доступ на 1 місяць (50 ⭐️)", callback_data="buy_sub_month")],
        [InlineKeyboardButton(text="♾ Доступ назавжди (400 ⭐️)", callback_data="buy_sub_forever")],
    ]

    if check_access(user_id):
        keyboard_buttons.insert(0, [
            InlineKeyboardButton(text="🚀 Відкрити додаток", web_app=WebAppInfo(url=WEB_APP_URL))
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        f"Вітаю! Це бот для оплати проїзду.\n\n{status_text}\n\nОберіть тариф або придбайте доступ за зірки Telegram:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    action = callback.data.replace("buy_", "")
    price_key = None
    
    if action == "1_ticket": price_key = "1_ticket"
    elif action == "sub_day": price_key = "sub_day"
    elif action == "sub_month": price_key = "sub_month"
    elif action == "sub_forever": price_key = "sub_forever"

    item = PRICES[price_key]
    prices = [LabeledPrice(label=item["title"], amount=item["price"])]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=item["title"],
        description=f"Придбання послуги: {item['title']} у Telegram Stars",
        payload=price_key,
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    if user_id not in users_db:
        users_db[user_id] = {"subscription_end": None, "tickets": 0}

    user = users_db[user_id]
    item = PRICES.get(payload)

    if item["type"] == "ticket":
        user["tickets"] += 1
        await message.answer("🎉 Оплата успішна! Вам нараховано 1 квиток. Натисніть /start, щоб відкрити додаток.")
    elif item["type"] == "sub":
        days = item["days"]
        base_date = max(user["subscription_end"] or datetime.now(), datetime.now())
        user["subscription_end"] = base_date + timedelta(days=days)
        
        date_str = user["subscription_end"].strftime("%d.%m.%Y о %H:%M")
        await message.answer(f"🎉 Підписку успішно активовано до {date_str}!\nНатисніть /start для запуску.")

# --- АДМІН-ПАНЕЛЬ (КЕРУВАННЯ ДОСТУПОМ) ---

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Вкажіть ID користувача, наприклад: `/add 123456789`", parse_mode="Markdown")
        return
    
    try:
        new_user_id = int(args[1])
        if new_user_id not in users_db:
            users_db[new_user_id] = {"subscription_end": None, "tickets": 0}
        
        users_db[new_user_id]["subscription_end"] = datetime.now() + timedelta(days=30)
        await message.answer(f"✅ Користувачу `{new_user_id}` надано доступ на 30 днів!", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Неправильний формат ID.")

@dp.message(Command("remove"))
async def cmd_remove(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Вкажіть ID користувача для видалення.")
        return
    
    try:
        rem_user_id = int(args[1])
        if rem_user_id in users_db:
            users_db[rem_user_id]["subscription_end"] = None
            users_db[rem_user_id]["tickets"] = 0
            await message.answer(f"🗑️ Доступ для користувача `{rem_user_id}` анульовано.", parse_mode="Markdown")
        else:
            await message.answer("❌ Користувача не знайдено в базі.")
    except ValueError:
        await message.answer("❌ Неправильний формат ID.")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))