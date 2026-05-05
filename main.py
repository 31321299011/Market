#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import re
import concurrent.futures
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any

import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
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
BOT_TOKEN = "8592158247:AAE-14WkYiiGU-2Yn4imByF7eDsDEznMQoQ"

# JSONBin কনফিগ
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# API এন্ডপয়েন্ট (একাধিক সোর্স)
API_SOURCES = {
    "coingecko": {
        "search": "https://api.coingecko.com/api/v3/search?query={query}",
        "price": "https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd",
        "markets": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false"
    },
    "coincap": {
        "search": "https://api.coincap.io/v2/assets?search={query}&limit=1",
        "price": "https://api.coincap.io/v2/assets/{id}",
        "markets": "https://api.coincap.io/v2/assets?limit=20"
    },
    "coinpaprika": {
        "search": "https://api.coinpaprika.com/v1/search?q={query}&c=currencies&limit=1",
        "price": "https://api.coinpaprika.com/v1/tickers/{id}",
        "markets": "https://api.coinpaprika.com/v1/tickers?quotes=USD&limit=20"
    }
}
FRANKFURTER_API = "https://api.frankfurter.app/latest?from=USD&to=BDT"

# মিনি অ্যাপ URL
MINI_APP_URL = "https://31321299011.github.io/Testhtml/"

# ------------------------- ইন-মেমোরি ক্যাশ -------------------------
_price_cache = {}
_search_cache = {}
_rate_cache = {}
CACHE_TTL_PRICE = 30
CACHE_TTL_SEARCH = 300
CACHE_TTL_RATE = 300
_cache_lock = threading.Lock()

# ------------------------- ভাষা টেক্সট -------------------------
TEXTS = {
    "bn": {
        "welcome": "🌟 ক্রিপ্টো মার্কেট বটে স্বাগতম! 🌟\n\nআমি লাইভ কয়েনের দাম USD ও BDT তে দেখাই।",
        "help": "❓ সাহায্য মেনু\n\n📌 কমান্ডসমূহ:\n/prices – শীর্ষ ২০ কয়েন\n/search <coin> – যেকোনো কয়েন খুঁজুন\n/cal – কনভার্টার (USD/BDT/ক্রিপ্টো)\n/lang – ভাষা পরিবর্তন\n/developer – বট তথ্য\n/stats – পরিসংখ্যান\n/help – এই মেনু\n\n📞 সাপোর্ট: @jhgmaing",
        "fetching": "🔄 তথ্য আনা হচ্ছে...",
        "top_coins": "💰 শীর্ষ ২০ ক্রিপ্টোকারেন্সি",
        "coin_not_found": "❌ কয়েন পাওয়া যায়নি!",
        "search_usage": "🔍 কয়েনের নাম লিখুন:",
        "conversion_result": "✅ রূপান্তর ফলাফল\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ রূপান্তর সম্ভব নয়। ফরম্যাট: /cal 1 btc to usd",
        "lang_changed": "✅ ভাষা পরিবর্তন করা হয়েছে বাংলায়!",
        "stats": "📊 পরিসংখ্যান\n\n👥 মোট ইউজার: {users}\n📝 মোট কমান্ড: {commands}",
        "developer": "👨‍💻 ডেভেলপার: @jhgmaing\n🛠 সহায়তা: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n🆔 ID: {id}",
        "cal_hint": "💡 উদাহরণ: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 ভাষা নির্বাচন করুন",
        "invalid_input": "❌ ভুল ইনপুট! আবার চেষ্টা করুন।",
        "button_prices": "📊 শীর্ষ কয়েন",
        "button_search": "🔍 কয়েন খুঁজুন",
        "button_calc": "🧮 ক্যালকুলেটর",
        "button_lang": "🌐 ভাষা",
        "button_help": "❓ সাহায্য",
        "button_dev": "👤 ডেভেলপার",
        "button_stats": "📈 পরিসংখ্যান",
        "button_miniapp": "🕹️ মিনি অ্যাপ",
        "search_prompt": "🔍 কয়েনের নাম লিখুন:",
        "calc_prompt": "🧮 ফরম্যাট: /cal [পরিমাণ] [মুদ্রা] to [মুদ্রা]",
        "no_price": "❌ দাম পাওয়া যায়নি।",
        "miniapp_msg": "👇 মিনি অ্যাপ ওপেন করতে নিচের বাটনে ক্লিক করুন"
    },
    "en": {
        "welcome": "🌟 Welcome to Crypto Market Bot! 🌟\n\nLive coin prices in USD & BDT.",
        "help": "❓ Help\n\n📌 Commands:\n/prices – Top 20 coins\n/search <coin> – Search any coin\n/cal – Converter\n/lang – Change language\n/developer – Bot info\n/stats – Statistics\n/help – This menu\n\n📞 Support: @jhgmaing",
        "fetching": "🔄 Fetching data...",
        "top_coins": "💰 Top 20 Cryptocurrencies",
        "coin_not_found": "❌ Coin not found!",
        "search_usage": "🔍 Enter coin name:",
        "conversion_result": "✅ Conversion Result\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ Conversion failed. Format: /cal 1 btc to usd",
        "lang_changed": "✅ Language changed to English!",
        "stats": "📊 Statistics\n\n👥 Total Users: {users}\n📝 Total Commands: {commands}",
        "developer": "👨‍💻 Developer: @jhgmaing\n🛠 Support: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n🆔 ID: {id}",
        "cal_hint": "💡 Examples: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 Select Language",
        "invalid_input": "❌ Invalid input!",
        "button_prices": "📊 Top Coins",
        "button_search": "🔍 Search Coin",
        "button_calc": "🧮 Calculator",
        "button_lang": "🌐 Language",
        "button_help": "❓ Help",
        "button_dev": "👤 Developer",
        "button_stats": "📈 Statistics",
        "button_miniapp": "🕹️ Mini App",
        "search_prompt": "🔍 Enter coin name:",
        "calc_prompt": "🧮 Format: /cal [amount] [currency] to [currency]",
        "no_price": "❌ Price not available.",
        "miniapp_msg": "👇 Click button below to open Mini App"
    },
    "ru": {
        "welcome": "🌟 Добро пожаловать в Crypto Market Bot! 🌟\n\nЦены в USD и BDT.",
        "help": "❓ Помощь\n\n📌 Команды:\n/prices – Топ 20 монет\n/search <coin> – Поиск\n/cal – Конвертер\n/lang – Язык\n/developer – О боте\n/stats – Статистика\n/help – Меню\n\n📞 Поддержка: @jhgmaing",
        "fetching": "🔄 Получение данных...",
        "top_coins": "💰 Топ 20 криптовалют",
        "coin_not_found": "❌ Монета не найдена!",
        "search_usage": "🔍 Введите название:",
        "conversion_result": "✅ Конвертация\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ Ошибка. Формат: /cal 1 btc to usd",
        "lang_changed": "✅ Язык изменён на русский!",
        "stats": "📊 Статистика\n\n👥 Пользователей: {users}\n📝 Команд: {commands}",
        "developer": "👨‍💻 Разработчик: @jhgmaing\n🛠 Поддержка: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n🆔 ID: {id}",
        "cal_hint": "💡 Примеры: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 Выберите язык",
        "invalid_input": "❌ Неверный ввод!",
        "button_prices": "📊 Топ монет",
        "button_search": "🔍 Поиск",
        "button_calc": "🧮 Калькулятор",
        "button_lang": "🌐 Язык",
        "button_help": "❓ Помощь",
        "button_dev": "👤 Разработчик",
        "button_stats": "📈 Статистика",
        "button_miniapp": "🕹️ Мини-приложение",
        "search_prompt": "🔍 Введите название монеты:",
        "calc_prompt": "🧮 Формат: /cal [сумма] [валюта] to [валюта]",
        "no_price": "❌ Цена недоступна.",
        "miniapp_msg": "👇 Нажмите кнопку ниже, чтобы открыть мини-приложение"
    },
    "hi": {
        "welcome": "🌟 क्रिप्टो मार्केट बॉट में आपका स्वागत है! 🌟\n\nUSD और BDT में मूल्य।",
        "help": "❓ सहायता\n\n📌 कमांड:\n/prices – शीर्ष 20 सिक्के\n/search <coin> – खोजें\n/cal – परिवर्तक\n/lang – भाषा\n/developer – बॉट जानकारी\n/stats – आँकड़े\n/help – मेनू\n\n📞 सहायता: @jhgmaing",
        "fetching": "🔄 डेटा लाया जा रहा है...",
        "top_coins": "💰 शीर्ष 20 क्रिप्टोकरेंसी",
        "coin_not_found": "❌ सिक्का नहीं मिला!",
        "search_usage": "🔍 सिक्के का नाम दर्ज करें:",
        "conversion_result": "✅ रूपांतरण\n\n{from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ रूपांतरण विफल। प्रारूप: /cal 1 btc to usd",
        "lang_changed": "✅ भाषा हिन्दी में बदली!",
        "stats": "📊 आँकड़े\n\n👥 उपयोगकर्ता: {users}\n📝 कमांड: {commands}",
        "developer": "👨‍💻 डेवलपर: @jhgmaing\n🛠 सहायता: @bot_developer_io",
        "price_info": "✅ {name} ({symbol})\n\n💵 USD: ${usd}\n🇧🇩 BDT: ৳{bdt}\n\n🆔 ID: {id}",
        "cal_hint": "💡 उदाहरण: /cal 1 btc to usd\n/cal 100 usdt to bdt",
        "select_lang": "🌍 भाषा चुनें",
        "invalid_input": "❌ अमान्य इनपुट!",
        "button_prices": "📊 शीर्ष सिक्के",
        "button_search": "🔍 खोजें",
        "button_calc": "🧮 कैलकुलेटर",
        "button_lang": "🌐 भाषा",
        "button_help": "❓ सहायता",
        "button_dev": "👤 डेवलपर",
        "button_stats": "📈 आँकड़े",
        "button_miniapp": "🕹️ मिनी ऐप",
        "search_prompt": "🔍 सिक्के का नाम दर्ज करें:",
        "calc_prompt": "🧮 प्रारूप: /cal [राशि] [मुद्रा] to [मुद्रा]",
        "no_price": "❌ कीमत उपलब्ध नहीं।",
        "miniapp_msg": "👇 मिनी ऐप खोलने के लिए नीचे बटन पर क्लिक करें"
    }
}

# লগিং সেটআপ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------- দ্রুততম API রেস -------------------------
def fastest_request(api_calls: List[Tuple[str, str, Dict]]) -> Optional[Any]:
    def fetch(method, url, params):
        try:
            if method == "GET":
                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(api_calls)) as executor:
        futures = []
        for method, url_tpl, params in api_calls:
            url = url_tpl.format(**params) if params else url_tpl
            futures.append(executor.submit(fetch, method, url, params if not url_tpl.startswith("http") else {}))
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                for f in futures:
                    f.cancel()
                return result
    return None

# ------------------------- API হেল্পার (ক্যাশিং সহ) -------------------------
def get_usd_bdt_rate() -> float:
    now = time.time()
    with _cache_lock:
        if "usd_bdt" in _rate_cache and (now - _rate_cache["usd_bdt"][1]) < CACHE_TTL_RATE:
            return _rate_cache["usd_bdt"][0]
    try:
        resp = requests.get(FRANKFURTER_API, timeout=4)
        rate = resp.json()["rates"]["BDT"]
        with _cache_lock:
            _rate_cache["usd_bdt"] = (rate, now)
        return rate
    except:
        with _cache_lock:
            if "usd_bdt" in _rate_cache:
                return _rate_cache["usd_bdt"][0]
        return 118.0

def search_coins(query: str) -> List[Dict]:
    query_lower = query.lower().strip()
    now = time.time()
    with _cache_lock:
        if query_lower in _search_cache and (now - _search_cache[query_lower][1]) < CACHE_TTL_SEARCH:
            return _search_cache[query_lower][0]
    calls = [
        ("GET", API_SOURCES["coingecko"]["search"].format(query=query), {}),
        ("GET", API_SOURCES["coincap"]["search"].format(query=query), {}),
        ("GET", API_SOURCES["coinpaprika"]["search"].format(query=query), {}),
    ]
    data = fastest_request(calls)
    coins = []
    if data:
        if "coins" in data:
            coins = data["coins"]
        elif "data" in data:
            assets = data.get("data", [])
            coins = [{"id": a["id"], "name": a["name"], "symbol": a["symbol"]} for a in assets]
        elif "currencies" in data:
            currencies = data.get("currencies", [])
            coins = [{"id": c["id"], "name": c["name"], "symbol": c["symbol"]} for c in currencies]
    with _cache_lock:
        _search_cache[query_lower] = (coins, now)
    return coins

def get_coin_price(coin_id: str) -> Optional[Dict]:
    now = time.time()
    with _cache_lock:
        if coin_id in _price_cache and (now - _price_cache[coin_id][1]) < CACHE_TTL_PRICE:
            return _price_cache[coin_id][0]
    calls = [
        ("GET", API_SOURCES["coingecko"]["price"].format(id=coin_id), {}),
        ("GET", API_SOURCES["coincap"]["price"].format(id=coin_id), {}),
        ("GET", API_SOURCES["coinpaprika"]["price"].format(id=coin_id), {}),
    ]
    data = fastest_request(calls)
    price_data = None
    if data:
        if coin_id in data and "usd" in data[coin_id]:
            price_data = data[coin_id]
        elif "data" in data and "priceUsd" in data["data"]:
            price_data = {"usd": float(data["data"]["priceUsd"])}
        elif "quotes" in data and "USD" in data["quotes"]:
            price_data = {"usd": data["quotes"]["USD"]["price"]}
    if price_data:
        with _cache_lock:
            _price_cache[coin_id] = (price_data, now)
    return price_data

def get_top_coins(limit: int = 20) -> List[Dict]:
    now = time.time()
    with _cache_lock:
        if "__top20__" in _price_cache and (now - _price_cache["__top20__"][1]) < CACHE_TTL_PRICE:
            return _price_cache["__top20__"][0]
    calls = [
        ("GET", API_SOURCES["coingecko"]["markets"], {}),
        ("GET", API_SOURCES["coincap"]["markets"], {}),
        ("GET", API_SOURCES["coinpaprika"]["markets"], {}),
    ]
    data = fastest_request(calls)
    result = []
    if not data:
        return result
    if isinstance(data, list) and len(data) > 0 and "current_price" in data[0]:
        result = data[:limit]
    elif "data" in data:
        assets = data["data"][:limit]
        for a in assets:
            result.append({
                "name": a["name"],
                "symbol": a["symbol"],
                "current_price": float(a["priceUsd"]),
                "price_change_percentage_24h": float(a.get("changePercent24Hr", 0))
            })
    elif isinstance(data, list) and len(data) > 0 and "quotes" in data[0]:
        for ticker in data[:limit]:
            result.append({
                "name": ticker["name"],
                "symbol": ticker["symbol"],
                "current_price": ticker["quotes"]["USD"]["price"],
                "price_change_percentage_24h": ticker["quotes"]["USD"].get("percent_change_24h", 0)
            })
    if result:
        with _cache_lock:
            _price_cache["__top20__"] = (result, now)
    return result

# ------------------------- JSONBin ডাটাবেজ -------------------------
def load_db() -> Dict:
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "X-Access-Key": JSONBIN_ACCESS_KEY}
    try:
        response = requests.get(JSONBIN_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("record", {})
    except Exception as e:
        logger.error(f"DB load error: {e}")
        return {"users": {}, "languages": ["bn", "en", "ru", "hi"], "stats": {"total_users": 0, "total_commands": 0}}

def save_db(data: Dict) -> bool:
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
    db = load_db()
    return db.get("users", {}).get(str(user_id), {}).get("lang", "bn")

def set_user_lang(user_id: int, lang: str) -> None:
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
    db = load_db()
    db["stats"]["total_commands"] = db["stats"].get("total_commands", 0) + 1
    save_db(db)

def get_stats() -> Tuple[int, int]:
    db = load_db()
    stats = db.get("stats", {})
    return stats.get("total_users", 0), stats.get("total_commands", 0)

# ------------------------- কনভার্টার -------------------------
async def convert_currency(amount: float, from_cur: str, to_cur: str) -> Optional[float]:
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

# ------------------------- কালারফুল কীবোর্ড -------------------------
def get_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [KeyboardButton("🔴 " + t["button_prices"]), KeyboardButton("🟢 " + t["button_search"])],
        [KeyboardButton("🟡 " + t["button_calc"]), KeyboardButton("🔵 " + t["button_lang"])],
        [KeyboardButton("🟣 " + t["button_help"]), KeyboardButton("🟠 " + t["button_dev"])],
        [KeyboardButton("⚪ " + t["button_stats"])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inline_menu(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [InlineKeyboardButton("🔴 " + t["button_prices"], callback_data="prices"),
         InlineKeyboardButton("🟢 " + t["button_search"], callback_data="search_prompt")],
        [InlineKeyboardButton("🟡 " + t["button_calc"], callback_data="calc_prompt")],
        [InlineKeyboardButton("🔵 " + t["button_lang"], callback_data="lang_menu"),
         InlineKeyboardButton("🟣 " + t["button_help"], callback_data="help")],
        [InlineKeyboardButton("🟠 " + t["button_dev"], callback_data="developer"),
         InlineKeyboardButton("⚪ " + t["button_stats"], callback_data="stats")],
        [InlineKeyboardButton("🛑 " + t["button_miniapp"], web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard_inline(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start")]])

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ])

def miniapp_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛑 " + t["button_miniapp"], web_app=WebAppInfo(url=MINI_APP_URL))]])

# ------------------------- হ্যান্ডলার -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
    if is_private:
        await update.message.reply_text(t["welcome"], reply_markup=get_reply_keyboard(lang))
        await update.message.reply_text(t["miniapp_msg"], reply_markup=miniapp_keyboard(lang))
    else:
        await update.message.reply_text(t["welcome"], reply_markup=get_inline_menu(lang))
    increment_command_count()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["help"], reply_markup=get_reply_keyboard(lang))
    else:
        await update.message.reply_text(t["help"], reply_markup=back_keyboard_inline(lang))
    increment_command_count()

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
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
        lines.append(f"{arrow} <b>{name} ({symbol})</b>\n   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {change:+.2f}%")
    text = "\n".join(lines)
    if is_private:
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_reply_keyboard(lang))
    else:
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard_inline(lang))
    increment_command_count()

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
    if not context.args:
        await update.message.reply_text(t["search_usage"])
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(t["fetching"])
    coins = search_coins(query)
    if not coins:
        await msg.edit_text(t["coin_not_found"])
        return
    coin = coins[0]
    price_data = get_coin_price(coin["id"])
    if not price_data or "usd" not in price_data:
        await msg.edit_text(t["no_price"])
        return
    usd = price_data["usd"]
    usd_bdt = get_usd_bdt_rate()
    bdt = usd * usd_bdt
    text = t["price_info"].format(name=coin['name'], symbol=coin['symbol'].upper(), usd=f"{usd:,.4f}", bdt=f"{bdt:,.2f}", id=coin['id'])
    text += f"\n\n💡 {t['cal_hint']}"
    keyboard = [
        [InlineKeyboardButton("🧮 Quick Convert", callback_data=f"calc_{coin['id']}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    increment_command_count()

async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(t["calc_prompt"])
        return
    text = " ".join(context.args)
    match = re.match(r"^([\d.]+)\s+(\w+)\s+to\s+(\w+)$", text, re.IGNORECASE)
    if not match:
        await update.message.reply_text(t["conversion_error"])
        return
    amount = float(match.group(1))
    from_cur = match.group(2).lower()
    to_cur = match.group(3).lower()
    msg = await update.message.reply_text(t["fetching"])
    result = await convert_currency(amount, from_cur, to_cur)
    if result is None:
        await msg.edit_text(t["conversion_error"])
        return
    to_amount = f"{result:,.8f}".rstrip('0').rstrip('.') if '.' in f"{result:,.8f}" else f"{result:,.0f}"
    text_out = t["conversion_result"].format(from_amount=f"{amount:,.4f}", from_currency=from_cur.upper(), to_amount=to_amount, to_currency=to_cur.upper())
    await msg.edit_text(text_out + f"\n\n💡 {t['cal_hint']}", parse_mode=ParseMode.HTML)
    increment_command_count()

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(TEXTS[lang]["select_lang"], reply_markup=lang_keyboard())
    increment_command_count()

async def developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["developer"], reply_markup=get_reply_keyboard(lang))
    else:
        await update.message.reply_text(t["developer"], reply_markup=back_keyboard_inline(lang))
    increment_command_count()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    users, commands = get_stats()
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["stats"].format(users=users, commands=commands), reply_markup=get_reply_keyboard(lang))
    else:
        await update.message.reply_text(t["stats"].format(users=users, commands=commands), reply_markup=back_keyboard_inline(lang))
    increment_command_count()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    if data == "start":
        await query.edit_message_text(t["welcome"], reply_markup=get_inline_menu(lang))
    elif data == "prices":
        await query.edit_message_text(t["fetching"])
        coins = get_top_coins(20)
        if not coins:
            await query.edit_message_text(t["no_price"], reply_markup=back_keyboard_inline(lang))
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
            lines.append(f"{arrow} <b>{name} ({symbol})</b>\n   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {change:+.2f}%")
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=back_keyboard_inline(lang))
    elif data == "search_prompt":
        await query.edit_message_text(t["search_prompt"], reply_markup=back_keyboard_inline(lang))
    elif data == "calc_prompt":
        await query.edit_message_text(t["calc_prompt"], reply_markup=back_keyboard_inline(lang))
    elif data == "lang_menu":
        await query.edit_message_text(t["select_lang"], reply_markup=lang_keyboard())
    elif data == "help":
        await query.edit_message_text(t["help"], reply_markup=back_keyboard_inline(lang))
    elif data == "developer":
        await query.edit_message_text(t["developer"], reply_markup=back_keyboard_inline(lang))
    elif data == "stats":
        users, commands = get_stats()
        await query.edit_message_text(t["stats"].format(users=users, commands=commands), reply_markup=back_keyboard_inline(lang))
    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_user_lang(user_id, new_lang)
        t_new = TEXTS[new_lang]
        await query.edit_message_text(t_new["lang_changed"], reply_markup=get_inline_menu(new_lang))
    elif data.startswith("calc_"):
        coin_id = data.replace("calc_", "")
        await query.edit_message_text(f"🧮 Enter conversion for {coin_id.upper()}:\nExample: /cal 1 {coin_id} to usd", reply_markup=back_keyboard_inline(lang))
    else:
        await query.edit_message_text(t["invalid_input"], reply_markup=back_keyboard_inline(lang))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        if text == "🔴 " + t["button_prices"]:
            await prices_command(update, context)
        elif text == "🟢 " + t["button_search"]:
            await update.message.reply_text(t["search_prompt"], reply_markup=get_reply_keyboard(lang))
        elif text == "🟡 " + t["button_calc"]:
            await update.message.reply_text(t["calc_prompt"], reply_markup=get_reply_keyboard(lang))
        elif text == "🔵 " + t["button_lang"]:
            await lang_command(update, context)
        elif text == "🟣 " + t["button_help"]:
            await help_command(update, context)
        elif text == "🟠 " + t["button_dev"]:
            await developer_command(update, context)
        elif text == "⚪ " + t["button_stats"]:
            await stats_command(update, context)
        else:
            await update.message.reply_text(t["help"], reply_markup=get_reply_keyboard(lang))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ------------------------- Flask হেলথ চেক -------------------------
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# ------------------------- মেইন -------------------------
def main():
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
    logger.info("Bot started with colorful buttons and Mini App.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
