#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import re
from datetime import datetime
from typing import Dict, Optional, List, Tuple

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ------------------------- কনফিগারেশন -------------------------
BOT_TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"

# JSONBin কনফিগ
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# API এন্ডপয়েন্ট
COINGECKO_API = "https://api.coingecko.com/api/v3"
FRANKFURTER_API = "https://api.frankfurter.app"

# ল্যাঙ্গুয়েজ ডিকশনারি
LANGUAGES = {
    "bn": "🇧🇩 বাংলা",
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "hi": "🇮🇳 हिन्दी"
}

# টেক্সট ট্রান্সলেশন (৪ ভাষায়)
TEXTS = {
    "bn": {
        "welcome": "🌟 ক্রিপ্টো মার্কেট বটে স্বাগতম! 🌟\n\nআমি লাইভ কয়েনের দাম USD ও BDT তে দেখাই। নিচের মেনু ব্যবহার করুন।",
        "help": "❓ সাহায্য মেনু\n\n📌 কমান্ডসমূহ:\n/prices – শীর্ষ ২০ কয়েন\n/search <coin> – যেকোনো কয়েন খুঁজুন\n/cal – কনভার্টার (USD/BDT/ক্রিপ্টো)\n/lang – ভাষা পরিবর্তন\n/developer – বট তথ্য\n/stats – পরিসংখ্যান\n/help – এই মেনু\n\n💡 উদাহরণ: /search bitcoin\n📞 সাপোর্ট: @jhgmaing",
        "fetching": "🔄 তথ্য আনা হচ্ছে...",
        "top_coins": "💰 শীর্ষ ২০ ক্রিপ্টোকারেন্সি",
        "coin_not_found": "❌ কয়েন পাওয়া যায়নি! নাম চেক করুন।",
        "search_usage": "🔍 যেকোনো কয়েনের নাম লিখুন:\nযেমন: /search bitcoin বা /search dogecoin",
        "conversion_result": "✅ রূপান্তর ফলাফল\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ রূপান্তর সম্ভব নয়। ফরম্যাট: /cal 1 btc to usd",
        "lang_changed": "✅ ভাষা পরিবর্তন করা হয়েছে বাংলায়!",
        "stats": "📊 বট পরিসংখ্যান\n\n👥 মোট ইউজার: {users}\n📝 মোট কমান্ড: {commands}",
        "developer": "👨‍💻 ডেভেলপার: @jhgmaing\n🛠 সহায়তা: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n📈 বর্তমান মূল্য:\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n📊 বাজার তথ্য:\n🆔 আইডি: {id}\n🕐 আপডেট: এইমাত্র",
        "cal_hint": "💡 উদাহরণ: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 ভাষা নির্বাচন করুন / Select language / Выберите язык / भाषा चुनें",
        "invalid_input": "❌ ভুল ইনপুট! আবার চেষ্টা করুন।",
        "button_prices": "📊 শীর্ষ কয়েন",
        "button_search": "🔍 কয়েন খুঁজুন",
        "button_calc": "🧮 ক্যালকুলেটর",
        "button_lang": "🌐 ভাষা",
        "button_help": "❓ সাহায্য",
        "button_dev": "👤 ডেভেলপার",
        "button_stats": "📈 পরিসংখ্যান",
        "search_prompt": "🔍 কয়েনের নাম লিখুন:",
        "calc_prompt": "🧮 ফরম্যাট: /cal [পরিমাণ] [মুদ্রা] to [মুদ্রা]\nযেমন: /cal 1 btc to usd",
        "no_price": "❌ দাম পাওয়া যায়নি।"
    },
    "en": {
        "welcome": "🌟 Welcome to Crypto Market Bot! 🌟\n\nI show live coin prices in USD & BDT. Use menu below.",
        "help": "❓ Help Menu\n\n📌 Commands:\n/prices – Top 20 coins\n/search <coin> – Search any coin\n/cal – Converter (USD/BDT/Crypto)\n/lang – Change language\n/developer – Bot info\n/stats – Statistics\n/help – This menu\n\n💡 Example: /search bitcoin\n📞 Support: @jhgmaing",
        "fetching": "🔄 Fetching data...",
        "top_coins": "💰 Top 20 Cryptocurrencies",
        "coin_not_found": "❌ Coin not found! Check the name.",
        "search_usage": "🔍 Enter a coin name:\ne.g. /search bitcoin or /search dogecoin",
        "conversion_result": "✅ Conversion Result\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ Conversion failed. Format: /cal 1 btc to usd",
        "lang_changed": "✅ Language changed to English!",
        "stats": "📊 Bot Statistics\n\n👥 Total Users: {users}\n📝 Total Commands: {commands}",
        "developer": "👨‍💻 Developer: @jhgmaing\n🛠 Support: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n📈 Current Price:\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n📊 Market Info:\n🆔 ID: {id}\n🕐 Updated: Just now",
        "cal_hint": "💡 Examples: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 Select language / ভাষা নির্বাচন / Выберите язык / भाषा चुनें",
        "invalid_input": "❌ Invalid input! Try again.",
        "button_prices": "📊 Top Coins",
        "button_search": "🔍 Search Coin",
        "button_calc": "🧮 Calculator",
        "button_lang": "🌐 Language",
        "button_help": "❓ Help",
        "button_dev": "👤 Developer",
        "button_stats": "📈 Statistics",
        "search_prompt": "🔍 Enter coin name:",
        "calc_prompt": "🧮 Format: /cal [amount] [currency] to [currency]\ne.g. /cal 1 btc to usd",
        "no_price": "❌ Price not available."
    },
    "ru": {
        "welcome": "🌟 Добро пожаловать в Crypto Market Bot! 🌟\n\nЯ показываю живые цены монет в USD и BDT. Используйте меню.",
        "help": "❓ Меню помощи\n\n📌 Команды:\n/prices – Топ 20 монет\n/search <coin> – Поиск монеты\n/cal – Конвертер (USD/BDT/Крипто)\n/lang – Сменить язык\n/developer – Информация о боте\n/stats – Статистика\n/help – Это меню\n\n💡 Пример: /search bitcoin\n📞 Поддержка: @jhgmaing",
        "fetching": "🔄 Получение данных...",
        "top_coins": "💰 Топ 20 криптовалют",
        "coin_not_found": "❌ Монета не найдена! Проверьте название.",
        "search_usage": "🔍 Введите название монеты:\nнапример /search bitcoin или /search dogecoin",
        "conversion_result": "✅ Результат конвертации\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ Ошибка конвертации. Формат: /cal 1 btc to usd",
        "lang_changed": "✅ Язык изменён на русский!",
        "stats": "📊 Статистика бота\n\n👥 Всего пользователей: {users}\n📝 Всего команд: {commands}",
        "developer": "👨‍💻 Разработчик: @jhgmaing\n🛠 Поддержка: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n📈 Текущая цена:\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n📊 Рыночная информация:\n🆔 ID: {id}\n🕐 Обновлено: только что",
        "cal_hint": "💡 Примеры: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 Выберите язык / Select language / ভাষা নির্বাচন / भाषा चुनें",
        "invalid_input": "❌ Неверный ввод! Попробуйте снова.",
        "button_prices": "📊 Топ монет",
        "button_search": "🔍 Поиск",
        "button_calc": "🧮 Калькулятор",
        "button_lang": "🌐 Язык",
        "button_help": "❓ Помощь",
        "button_dev": "👤 Разработчик",
        "button_stats": "📈 Статистика",
        "search_prompt": "🔍 Введите название монеты:",
        "calc_prompt": "🧮 Формат: /cal [сумма] [валюта] to [валюта]\nнапример /cal 1 btc to usd",
        "no_price": "❌ Цена недоступна."
    },
    "hi": {
        "welcome": "🌟 क्रिप्टो मार्केट बॉट में आपका स्वागत है! 🌟\n\nमैं USD और BDT में लाइव सिक्के की कीमतें दिखाता हूँ। नीचे दिए मेनू का उपयोग करें।",
        "help": "❓ सहायता मेनू\n\n📌 कमांड:\n/prices – शीर्ष 20 सिक्के\n/search <coin> – कोई भी सिक्का खोजें\n/cal – परिवर्तक (USD/BDT/क्रिप्टो)\n/lang – भाषा बदलें\n/developer – बॉट जानकारी\n/stats – आँकड़े\n/help – यह मेनू\n\n💡 उदाहरण: /search bitcoin\n📞 सहायता: @jhgmaing",
        "fetching": "🔄 डेटा लाया जा रहा है...",
        "top_coins": "💰 शीर्ष 20 क्रिप्टोकरेंसी",
        "coin_not_found": "❌ सिक्का नहीं मिला! नाम जाँचें।",
        "search_usage": "🔍 सिक्के का नाम दर्ज करें:\nजैसे /search bitcoin या /search dogecoin",
        "conversion_result": "✅ रूपांतरण परिणाम\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ रूपांतरण विफल। प्रारूप: /cal 1 btc to usd",
        "lang_changed": "✅ भाषा हिन्दी में बदल दी गई!",
        "stats": "📊 बॉट आँकड़े\n\n👥 कुल उपयोगकर्ता: {users}\n📝 कुल कमांड: {commands}",
        "developer": "👨‍💻 डेवलपर: @jhgmaing\n🛠 सहायता: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n📈 वर्तमान मूल्य:\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n📊 बाज़ार जानकारी:\n🆔 ID: {id}\n🕐 अपडेट किया गया: अभी",
        "cal_hint": "💡 उदाहरण: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 भाषा चुनें / Select language / ভাষা নির্বাচন / Выберите язык",
        "invalid_input": "❌ अमान्य इनपुट! पुनः प्रयास करें।",
        "button_prices": "📊 शीर्ष सिक्के",
        "button_search": "🔍 सिक्का खोजें",
        "button_calc": "🧮 कैलकुलेटर",
        "button_lang": "🌐 भाषा",
        "button_help": "❓ सहायता",
        "button_dev": "👤 डेवलपर",
        "button_stats": "📈 आँकड़े",
        "search_prompt": "🔍 सिक्के का नाम दर्ज करें:",
        "calc_prompt": "🧮 प्रारूप: /cal [राशि] [मुद्रा] to [मुद्रा]\nजैसे /cal 1 btc to usd",
        "no_price": "❌ कीमत उपलब्ध नहीं है।"
    }
}

# লগিং সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------- JSONBin হেল্পার -------------------------
def load_db() -> Dict:
    """JSONBin থেকে ডাটাবেজ লোড করে।"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY
    }
    try:
        response = requests.get(JSONBIN_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("record", {})
    except Exception as e:
        logger.error(f"DB load error: {e}")
        return {
            "users": {},
            "languages": ["bn", "en", "ru", "hi"],
            "stats": {"total_users": 0, "total_commands": 0}
        }

def save_db(data: Dict) -> bool:
    """JSONBin-এ ডাটাবেজ সেভ করে।"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(JSONBIN_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"DB save error: {e}")
        return False

def get_user_lang(user_id: int) -> str:
    """ইউজারের সংরক্ষিত ভাষা রিটার্ন করে, না থাকলে ডিফল্ট 'en'।"""
    db = load_db()
    return db.get("users", {}).get(str(user_id), {}).get("lang", "en")

def set_user_lang(user_id: int, lang: str) -> None:
    """ইউজারের ভাষা সংরক্ষণ করে।"""
    db = load_db()
    if "users" not in db:
        db["users"] = {}
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"lang": lang, "first_seen": datetime.utcnow().isoformat()}
        db["stats"]["total_users"] = db["stats"].get("total_users", 0) + 1
    else:
        db["users"][str(user_id)]["lang"] = lang
    save_db(db)

def increment_command_count() -> None:
    """কমান্ড কাউন্ট বাড়ায়।"""
    db = load_db()
    db["stats"]["total_commands"] = db["stats"].get("total_commands", 0) + 1
    save_db(db)

def get_stats() -> Tuple[int, int]:
    """স্ট্যাটিস্টিক্স রিটার্ন করে।"""
    db = load_db()
    stats = db.get("stats", {})
    return stats.get("total_users", 0), stats.get("total_commands", 0)

# ------------------------- API হেল্পার -------------------------
def get_usd_bdt_rate() -> float:
    """Frankfurter API থেকে লাইভ USD → BDT রেট আনে।"""
    try:
        resp = requests.get(f"{FRANKFURTER_API}/latest?from=USD&to=BDT", timeout=5)
        data = resp.json()
        return data["rates"]["BDT"]
    except Exception as e:
        logger.error(f"Forex error: {e}")
        return 118.0  # ফলব্যাক রেট

def search_coins(query: str) -> List[Dict]:
    """CoinGecko search API ব্যবহার করে কয়েন খোঁজে।"""
    try:
        resp = requests.get(f"{COINGECKO_API}/search?query={query}", timeout=10)
        data = resp.json()
        return data.get("coins", [])
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def get_coin_price(coin_id: str) -> Optional[Dict]:
    """নির্দিষ্ট কয়েনের দাম (USD) আনে।"""
    try:
        resp = requests.get(
            f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd",
            timeout=10
        )
        data = resp.json()
        return data.get(coin_id, {})
    except Exception as e:
        logger.error(f"Price error: {e}")
        return None

def get_top_coins(limit: int = 20) -> List[Dict]:
    """শীর্ষ কয়েনের তালিকা আনে (মার্কেট ক্যাপ অনুযায়ী)।"""
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false",
            timeout=15
        )
        return resp.json()
    except Exception as e:
        logger.error(f"Top coins error: {e}")
        return []

# ------------------------- কনভার্সন হেল্পার -------------------------
async def convert_currency(amount: float, from_cur: str, to_cur: str) -> Optional[float]:
    """ক্রিপ্টো ও ফিয়াট কনভার্ট করে।"""
    from_cur = from_cur.lower()
    to_cur = to_cur.lower()
    
    if from_cur in ["usd", "bdt"] and to_cur in ["usd", "bdt"]:
        usd_bdt = get_usd_bdt_rate()
        if from_cur == "usd" and to_cur == "bdt":
            return amount * usd_bdt
        elif from_cur == "bdt" and to_cur == "usd":
            return amount / usd_bdt
        else:
            return amount
    
    crypto_id = from_cur if from_cur not in ["usd", "bdt"] else to_cur
    coins = search_coins(crypto_id)
    if not coins:
        return None
    coin = coins[0]
    price_data = get_coin_price(coin["id"])
    if not price_data or "usd" not in price_data:
        return None
    usd_price = price_data["usd"]
    usd_bdt = get_usd_bdt_rate()
    
    if from_cur == crypto_id and to_cur == "usd":
        return amount * usd_price
    elif from_cur == crypto_id and to_cur == "bdt":
        return amount * usd_price * usd_bdt
    elif from_cur == "usd" and to_cur == crypto_id:
        return amount / usd_price if usd_price != 0 else None
    elif from_cur == "bdt" and to_cur == crypto_id:
        usd_amount = amount / usd_bdt
        return usd_amount / usd_price if usd_price != 0 else None
    return None

# ------------------------- বাটন জেনারেটর -------------------------
def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [InlineKeyboardButton(t["button_prices"], callback_data="prices")],
        [InlineKeyboardButton(t["button_search"], callback_data="search_prompt")],
        [InlineKeyboardButton(t["button_calc"], callback_data="calc_prompt")],
        [
            InlineKeyboardButton(t["button_lang"], callback_data="lang_menu"),
            InlineKeyboardButton(t["button_help"], callback_data="help")
        ],
        [
            InlineKeyboardButton(t["button_dev"], callback_data="developer"),
            InlineKeyboardButton(t["button_stats"], callback_data="stats")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    return InlineKeyboardMarkup(keyboard)

# ------------------------- হ্যান্ডলার -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(
        t["welcome"],
        reply_markup=main_menu_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    increment_command_count()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(
        t["help"],
        reply_markup=back_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    increment_command_count()

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    msg = await update.message.reply_text(t["fetching"])
    coins = get_top_coins(20)
    if not coins:
        await msg.edit_text(t["no_price"])
        return
    usd_bdt = get_usd_bdt_rate()
    lines = [f"<b>{t['top_coins']}</b>\n"]
    for coin in coins[:20]:
        name = coin['name']
        symbol = coin['symbol'].upper()
        usd = coin['current_price']
        bdt = usd * usd_bdt
        change = coin.get('price_change_percentage_24h', 0)
        arrow = "📈" if change >= 0 else "📉"
        lines.append(
            f"{arrow} <b>{name} ({symbol})</b>\n"
            f"   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {change:+.2f}%"
        )
    text = "\n".join(lines)
    await msg.edit_text(
        text,
        reply_markup=back_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    increment_command_count()

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if not context.args:
        await update.message.reply_text(
            t["search_usage"],
            reply_markup=back_keyboard(lang)
        )
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(t["fetching"])
    coins = search_coins(query)
    if not coins:
        await msg.edit_text(t["coin_not_found"], reply_markup=back_keyboard(lang))
        return
    coin = coins[0]
    price_data = get_coin_price(coin["id"])
    if not price_data or "usd" not in price_data:
        await msg.edit_text(t["no_price"], reply_markup=back_keyboard(lang))
        return
    usd = price_data["usd"]
    usd_bdt = get_usd_bdt_rate()
    bdt = usd * usd_bdt
    text = t["price_info"].format(
        name=coin['name'],
        symbol=coin['symbol'].upper(),
        usd=f"{usd:,.4f}",
        bdt=f"{bdt:,.2f}",
        id=coin['id']
    )
    text += f"\n\n💡 {t['cal_hint']}"
    keyboard = [
        [InlineKeyboardButton("🧮 Quick Convert", callback_data=f"calc_{coin['id']}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ]
    await msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    increment_command_count()

async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            t["calc_prompt"],
            reply_markup=back_keyboard(lang)
        )
        return
    text = " ".join(context.args)
    match = re.match(r"^([\d.]+)\s+(\w+)\s+to\s+(\w+)$", text, re.IGNORECASE)
    if not match:
        await update.message.reply_text(
            t["conversion_error"],
            reply_markup=back_keyboard(lang)
        )
        return
    amount = float(match.group(1))
    from_cur = match.group(2).lower()
    to_cur = match.group(3).lower()
    msg = await update.message.reply_text(t["fetching"])
    result = await convert_currency(amount, from_cur, to_cur)
    if result is None:
        await msg.edit_text(t["conversion_error"], reply_markup=back_keyboard(lang))
        return
    to_amount = f"{result:,.8f}".rstrip('0').rstrip('.') if '.' in f"{result:,.8f}" else f"{result:,.0f}"
    text_out = t["conversion_result"].format(
        from_amount=f"{amount:,.4f}",
        from_currency=from_cur.upper(),
        to_amount=to_amount,
        to_currency=to_cur.upper()
    )
    await msg.edit_text(
        text_out + f"\n\n💡 {t['cal_hint']}",
        reply_markup=back_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    increment_command_count()

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(
        t["select_lang"],
        reply_markup=language_keyboard()
    )
    increment_command_count()

async def developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(
        t["developer"],
        reply_markup=back_keyboard(lang)
    )
    increment_command_count()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    users, commands = get_stats()
    await update.message.reply_text(
        t["stats"].format(users=users, commands=commands),
        reply_markup=back_keyboard(lang)
    )
    increment_command_count()

# ------------------------- ক্যালব্যাক কোয়েরি হ্যান্ডলার -------------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    
    if data == "start":
        await query.edit_message_text(
            t["welcome"],
            reply_markup=main_menu_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
    elif data == "prices":
        await query.edit_message_text(t["fetching"])
        coins = get_top_coins(20)
        if not coins:
            await query.edit_message_text(t["no_price"], reply_markup=back_keyboard(lang))
            return
        usd_bdt = get_usd_bdt_rate()
        lines = [f"<b>{t['top_coins']}</b>\n"]
        for coin in coins[:20]:
            name = coin['name']
            symbol = coin['symbol'].upper()
            usd = coin['current_price']
            bdt = usd * usd_bdt
            change = coin.get('price_change_percentage_24h', 0)
            arrow = "📈" if change >= 0 else "📉"
            lines.append(
                f"{arrow} <b>{name} ({symbol})</b>\n"
                f"   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {change:+.2f}%"
            )
        text = "\n".join(lines)
        await query.edit_message_text(
            text,
            reply_markup=back_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
    elif data == "search_prompt":
        await query.edit_message_text(
            t["search_prompt"],
            reply_markup=back_keyboard(lang)
        )
    elif data == "calc_prompt":
        await query.edit_message_text(
            t["calc_prompt"],
            reply_markup=back_keyboard(lang)
        )
    elif data == "lang_menu":
        await query.edit_message_text(
            t["select_lang"],
            reply_markup=language_keyboard()
        )
    elif data == "help":
        await query.edit_message_text(
            t["help"],
            reply_markup=back_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
    elif data == "developer":
        await query.edit_message_text(
            t["developer"],
            reply_markup=back_keyboard(lang)
        )
    elif data == "stats":
        users, commands = get_stats()
        await query.edit_message_text(
            t["stats"].format(users=users, commands=commands),
            reply_markup=back_keyboard(lang)
        )
    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_user_lang(user_id, new_lang)
        t_new = TEXTS[new_lang]
        await query.edit_message_text(
            t_new["lang_changed"],
            reply_markup=main_menu_keyboard(new_lang)
        )
    elif data.startswith("calc_"):
        coin_id = data.replace("calc_", "")
        await query.edit_message_text(
            f"🧮 Enter conversion for {coin_id.upper()}:\n"
            f"Example: /cal 1 {coin_id} to usd",
            reply_markup=back_keyboard(lang)
        )
    else:
        await query.edit_message_text(t["invalid_input"], reply_markup=back_keyboard(lang))

# ------------------------- মেসেজ হ্যান্ডলার -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type == "private":
        user_id = update.effective_user.id
        lang = get_user_lang(user_id)
        t = TEXTS[lang]
        await update.message.reply_text(
            t["help"],
            reply_markup=main_menu_keyboard(lang)
        )

# ------------------------- এরর হ্যান্ডলার -------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ------------------------- মেইন -------------------------
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("cal", cal_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("developer", developer_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
