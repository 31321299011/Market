#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import re
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    constants,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ========== কনফিগারেশন ==========
BOT_TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"

# JSONBin.io কনফিগ
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# ডেভেলপার ইনফো
DEVELOPER_USERNAMES = ["@jhgmaing", "@bot_developer_io"]

# কয়েনগেকো API (ফ্রি, রেট লিমিট ৩০/মিনিট)
COINGECKO_API = "https://api.coingecko.com/api/v3"
SUPPORTED_VS_CURRENCIES = ["usd", "bdt"]

# ক্যাশ সেটিংস
CACHE_TTL_SECONDS = 120  # ২ মিনিট
CACHE_COINS_LIST_TTL = 3600  # ১ ঘন্টা

# ভাষা কোড
LANGUAGES = {
    "en": "English",
    "bn": "বাংলা",
    "ru": "Русский",
    "hi": "हिन्दी",
}

# ডিফল্ট ভাষা
DEFAULT_LANG = "en"

# ========== গ্লোবাল ক্যাশ ==========
price_cache: Dict[str, Tuple[float, float, datetime]] = {}  # symbol -> (usd_price, bdt_price, timestamp)
coins_list_cache: Optional[List[Dict]] = None
coins_list_cache_time: Optional[datetime] = None
cache_lock = threading.RLock()

# ========== লগিং সেটআপ ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ========== JSONBin হেল্পার ফাংশন ==========
def fetch_jsonbin_data() -> dict:
    """JSONBin থেকে সম্পূর্ণ ডাটা ফেচ করা"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
    }
    try:
        resp = requests.get(JSONBIN_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("record", {})
    except Exception as e:
        logger.error(f"JSONBin fetch error: {e}")
        # ডিফল্ট স্ট্রাকচার রিটার্ন
        return {
            "users": {},
            "languages": ["bn", "en", "ru", "hi"],
            "stats": {"total_users": 0, "total_commands": 0},
        }

def update_jsonbin_data(record: dict) -> bool:
    """JSONBin এ ডাটা আপডেট করা"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.put(JSONBIN_URL, headers=headers, json=record, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"JSONBin update error: {e}")
        return False

def get_user_language(user_id: int) -> str:
    """ইউজারের ভাষা রিটার্ন করে, না থাকলে ডিফল্ট"""
    data = fetch_jsonbin_data()
    users = data.get("users", {})
    user_str = str(user_id)
    return users.get(user_str, {}).get("lang", DEFAULT_LANG)

def set_user_language(user_id: int, lang: str) -> bool:
    """ইউজারের ভাষা সেট করে"""
    data = fetch_jsonbin_data()
    users = data.get("users", {})
    user_str = str(user_id)
    if user_str not in users:
        users[user_str] = {}
    users[user_str]["lang"] = lang
    data["users"] = users
    # পরিসংখ্যান আপডেট
    data["stats"]["total_users"] = len(users)
    return update_jsonbin_data(data)

def increment_command_stats():
    """কমান্ড স্ট্যাট আপডেট (ব্যাকগ্রাউন্ডে)"""
    try:
        data = fetch_jsonbin_data()
        data["stats"]["total_commands"] = data.get("stats", {}).get("total_commands", 0) + 1
        update_jsonbin_data(data)
    except:
        pass

# ========== ভাষা স্ট্রিং ==========
STRINGS = {
    "welcome": {
        "en": "🌟 Welcome to Crypto Market Bot! 🌟\n\nI show live prices of any coin in USD/BDT.\nUse /help for commands.",
        "bn": "🌟 ক্রিপ্টো মার্কেট বটে স্বাগতম! 🌟\n\nআমি যেকোনো কয়েনের লাইভ মূল্য USD/BDT তে দেখাই।\nকমান্ডের জন্য /help ব্যবহার করুন।",
        "ru": "🌟 Добро пожаловать в Crypto Market Bot! 🌟\n\nЯ показываю живые цены любой монеты в USD/BDT.\nИспользуйте /help для команд.",
        "hi": "🌟 क्रिप्टो मार्केट बॉट में स्वागत है! 🌟\n\nमैं किसी भी सिक्के की लाइव कीमत USD/BDT में दिखाता हूँ।\nकमांड के लिए /help का उपयोग करें।",
    },
    "help": {
        "en": (
            "❓ **Help Menu**\n\n"
            "📌 Commands:\n"
            "/prices – Top 20 coins\n"
            "/search <coin> – Search any coin\n"
            "/cal – Currency converter\n"
            "/lang – Change language\n"
            "/developer – Bot info\n"
            "/stats – Statistics\n"
            "/help – This menu\n\n"
            "📌 Examples:\n"
            "/search bitcoin\n"
            "/search dogecoin\n"
            "/cal 100 usd to bdt\n\n"
            "💡 Support: @jhgmaing"
        ),
        "bn": (
            "❓ **সাহায্য মেনু**\n\n"
            "📌 কমান্ডসমূহ:\n"
            "/prices – শীর্ষ ২০ কয়েন\n"
            "/search <কয়েন> – যেকোনো কয়েন সার্চ\n"
            "/cal – কারেন্সি কনভার্টার\n"
            "/lang – ভাষা পরিবর্তন\n"
            "/developer – বট তথ্য\n"
            "/stats – পরিসংখ্যান\n"
            "/help – এই মেনু\n\n"
            "📌 উদাহরণ:\n"
            "/search bitcoin\n"
            "/search dogecoin\n"
            "/cal 100 usd to bdt\n\n"
            "💡 সাপোর্ট: @jhgmaing"
        ),
        "ru": (
            "❓ **Меню справки**\n\n"
            "📌 Команды:\n"
            "/prices – Топ 20 монет\n"
            "/search <монета> – Поиск монеты\n"
            "/cal – Конвертер валют\n"
            "/lang – Сменить язык\n"
            "/developer – Информация о боте\n"
            "/stats – Статистика\n"
            "/help – Это меню\n\n"
            "📌 Примеры:\n"
            "/search bitcoin\n"
            "/search dogecoin\n"
            "/cal 100 usd to bdt\n\n"
            "💡 Поддержка: @jhgmaing"
        ),
        "hi": (
            "❓ **सहायता मेनू**\n\n"
            "📌 कमांड:\n"
            "/prices – शीर्ष 20 सिक्के\n"
            "/search <सिक्का> – कोई भी सिक्का खोजें\n"
            "/cal – मुद्रा परिवर्तक\n"
            "/lang – भाषा बदलें\n"
            "/developer – बॉट जानकारी\n"
            "/stats – आंकड़े\n"
            "/help – यह मेनू\n\n"
            "📌 उदाहरण:\n"
            "/search bitcoin\n"
            "/search dogecoin\n"
            "/cal 100 usd to bdt\n\n"
            "💡 सहायता: @jhgmaing"
        ),
    },
    "prices_header": {
        "en": "💰 **Live Prices**\n\n",
        "bn": "💰 **লাইভ মূল্য**\n\n",
        "ru": "💰 **Живые цены**\n\n",
        "hi": "💰 **लाइव कीमतें**\n\n",
    },
    "search_found": {
        "en": "✅ **{name} ({symbol})**\n\n📈 Current Price:\n💵 USD: ${usd:.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 Market Info:\n🆔 ID: {id}\n🕐 Updated: Just now\n\n💡 Commands:\n/cal 1 {symbol_lower} to usd\n/cal 100 usd to {symbol_lower}",
        "bn": "✅ **{name} ({symbol})**\n\n📈 বর্তমান মূল্য:\n💵 USD: ${usd:.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 বাজার তথ্য:\n🆔 আইডি: {id}\n🕐 আপডেট: এইমাত্র\n\n💡 কমান্ড:\n/cal 1 {symbol_lower} to usd\n/cal 100 usd to {symbol_lower}",
        "ru": "✅ **{name} ({symbol})**\n\n📈 Текущая цена:\n💵 USD: ${usd:.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 Информация:\n🆔 ID: {id}\n🕐 Обновлено: Только что\n\n💡 Команды:\n/cal 1 {symbol_lower} to usd\n/cal 100 usd to {symbol_lower}",
        "hi": "✅ **{name} ({symbol})**\n\n📈 वर्तमान मूल्य:\n💵 USD: ${usd:.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 बाजार जानकारी:\n🆔 ID: {id}\n🕐 अपडेट किया गया: अभी\n\n💡 कमांड:\n/cal 1 {symbol_lower} to usd\n/cal 100 usd to {symbol_lower}",
    },
    "search_not_found": {
        "en": "❌ Coin not found! Please check the name and try again.\nExample: /search bitcoin",
        "bn": "❌ কয়েন পাওয়া যায়নি! নামটি যাচাই করে আবার চেষ্টা করুন।\nউদাহরণ: /search bitcoin",
        "ru": "❌ Монета не найдена! Проверьте название.\nПример: /search bitcoin",
        "hi": "❌ सिक्का नहीं मिला! कृपया नाम जांचें।\nउदाहरण: /search bitcoin",
    },
    "search_usage": {
        "en": "🔍 Please provide a coin name or symbol.\nUsage: /search bitcoin",
        "bn": "🔍 দয়া করে একটি কয়েনের নাম বা সিম্বল দিন।\nব্যবহার: /search bitcoin",
        "ru": "🔍 Укажите название монеты.\nИспользование: /search bitcoin",
        "hi": "🔍 कृपया सिक्के का नाम या प्रतीक दें।\nउपयोग: /search bitcoin",
    },
    "searching": {
        "en": "🔄 Searching for {query}...",
        "bn": "🔄 {query} খোঁজা হচ্ছে...",
        "ru": "🔄 Поиск {query}...",
        "hi": "🔄 {query} की खोज हो रही है...",
    },
    "conversion_result": {
        "en": "✅ **Conversion Result**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "bn": "✅ **রূপান্তর ফলাফল**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "ru": "✅ **Результат конвертации**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "hi": "✅ **रूपांतरण परिणाम**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
    },
    "conversion_error": {
        "en": "❌ Conversion failed. Check format: /cal 100 usd to bdt",
        "bn": "❌ রূপান্তর ব্যর্থ। ফরম্যাট: /cal 100 usd to bdt",
        "ru": "❌ Ошибка конвертации. Формат: /cal 100 usd to bdt",
        "hi": "❌ रूपांतरण विफल। प्रारूप: /cal 100 usd to bdt",
    },
    "lang_select": {
        "en": "🌍 Select language / ভাষা নির্বাচন করুন:",
        "bn": "🌍 ভাষা নির্বাচন করুন / Select language:",
        "ru": "🌍 Выберите язык / Select language:",
        "hi": "🌍 भाषा चुनें / Select language:",
    },
    "lang_changed": {
        "en": "✅ Language changed to English!",
        "bn": "✅ ভাষা পরিবর্তন করে বাংলা করা হয়েছে!",
        "ru": "✅ Язык изменён на Русский!",
        "hi": "✅ भाषा बदलकर हिन्दी कर दी गई है!",
    },
    "developer_info": {
        "en": "👨‍💻 **Developer Info**\n\nBot created by:\n• @jhgmaing\n• @bot_developer_io\n\nVersion: 2.0.0\nUpdates: Real-time crypto prices",
        "bn": "👨‍💻 **ডেভেলপার তথ্য**\n\nবট তৈরি করেছেন:\n• @jhgmaing\n• @bot_developer_io\n\nভার্সন: 2.0.0\nআপডেট: রিয়েল-টাইম ক্রিপ্টো মূল্য",
        "ru": "👨‍💻 **Информация о разработчике**\n\nБот создан:\n• @jhgmaing\n• @bot_developer_io\n\nВерсия: 2.0.0\nОбновления: Реальные цены",
        "hi": "👨‍💻 **डेवलपर जानकारी**\n\nबॉट द्वारा बनाया गया:\n• @jhgmaing\n• @bot_developer_io\n\nसंस्करण: 2.0.0\nअपडेट: रियल-टाइम क्रिप्टो कीमतें",
    },
    "stats_text": {
        "en": "📊 **Bot Statistics**\n\n👥 Total Users: {users}\n🔄 Total Commands: {commands}",
        "bn": "📊 **বট পরিসংখ্যান**\n\n👥 মোট ব্যবহারকারী: {users}\n🔄 মোট কমান্ড: {commands}",
        "ru": "📊 **Статистика бота**\n\n👥 Всего пользователей: {users}\n🔄 Всего команд: {commands}",
        "hi": "📊 **बॉट आंकड़े**\n\n👥 कुल उपयोगकर्ता: {users}\n🔄 कुल कमांड: {commands}",
    },
    "inline_keyboard": {
        "prices": {"en": "💰 Prices", "bn": "💰 মূল্য", "ru": "💰 Цены", "hi": "💰 कीमतें"},
        "search": {"en": "🔍 Search", "bn": "🔍 সার্চ", "ru": "🔍 Поиск", "hi": "🔍 खोज"},
        "help": {"en": "❓ Help", "bn": "❓ সাহায্য", "ru": "❓ Помощь", "hi": "❓ सहायता"},
        "lang": {"en": "🌐 Language", "bn": "🌐 ভাষা", "ru": "🌐 Язык", "hi": "🌐 भाषा"},
        "cal": {"en": "🔄 Convert", "bn": "🔄 রূপান্তর", "ru": "🔄 Конверт", "hi": "🔄 बदलें"},
    },
}

def get_string(key: str, lang: str, **kwargs) -> str:
    """ভাষা অনুযায়ী স্ট্রিং ফরম্যাট করে রিটার্ন"""
    string_dict = STRINGS.get(key, {})
    text = string_dict.get(lang, string_dict.get("en", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text

# ========== কয়েনগেকো হেল্পার ==========
def fetch_coins_list() -> List[Dict]:
    """CoinGecko থেকে সব কয়েনের লিস্ট ফেচ (ক্যাশ সহ)"""
    global coins_list_cache, coins_list_cache_time
    with cache_lock:
        if (coins_list_cache is not None and coins_list_cache_time is not None and
                datetime.now() - coins_list_cache_time < timedelta(seconds=CACHE_COINS_LIST_TTL)):
            return coins_list_cache

    try:
        resp = requests.get(f"{COINGECKO_API}/coins/list", timeout=15)
        resp.raise_for_status()
        coins = resp.json()
        with cache_lock:
            coins_list_cache = coins
            coins_list_cache_time = datetime.now()
        return coins
    except Exception as e:
        logger.error(f"Failed to fetch coins list: {e}")
        # ক্যাশ থাকলে সেটাই রিটার্ন
        if coins_list_cache is not None:
            return coins_list_cache
        # না থাকলে খালি লিস্ট
        return []

def search_coin_id(query: str) -> Optional[Dict]:
    """কয়েনের নাম/সিম্বল দিয়ে ID খোঁজা (উন্নত ম্যাচিং)"""
    coins = fetch_coins_list()
    if not coins:
        return None

    query_lower = query.lower().strip()

    # প্রথমে exact symbol match (case-insensitive)
    for coin in coins:
        if coin.get("symbol", "").lower() == query_lower:
            return coin

    # exact name match
    for coin in coins:
        if coin.get("name", "").lower() == query_lower:
            return coin

    # partial symbol match (শুরুতে)
    for coin in coins:
        if coin.get("symbol", "").lower().startswith(query_lower):
            return coin

    # partial name match (শুরুতে)
    for coin in coins:
        if coin.get("name", "").lower().startswith(query_lower):
            return coin

    # contains in name
    for coin in coins:
        if query_lower in coin.get("name", "").lower():
            return coin

    return None

def get_cached_price(coin_id: str) -> Optional[Tuple[float, float]]:
    """ক্যাশ থেকে দাম বের করা"""
    with cache_lock:
        if coin_id in price_cache:
            usd, bdt, ts = price_cache[coin_id]
            if datetime.now() - ts < timedelta(seconds=CACHE_TTL_SECONDS):
                return usd, bdt
    return None

def cache_price(coin_id: str, usd_price: float, bdt_price: float):
    """দাম ক্যাশে রাখা"""
    with cache_lock:
        price_cache[coin_id] = (usd_price, bdt_price, datetime.now())

def fetch_live_price(coin_id: str) -> Optional[Tuple[float, float]]:
    """CoinGecko থেকে সরাসরি দাম আনা (USD + BDT)"""
    # ক্যাশ চেক
    cached = get_cached_price(coin_id)
    if cached:
        return cached

    params = {
        "ids": coin_id,
        "vs_currencies": ",".join(SUPPORTED_VS_CURRENCIES),
    }
    try:
        resp = requests.get(f"{COINGECKO_API}/simple/price", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        coin_data = data.get(coin_id, {})
        usd = coin_data.get("usd")
        bdt = coin_data.get("bdt")
        if usd is not None and bdt is not None:
            cache_price(coin_id, usd, bdt)
            return usd, bdt
        return None
    except Exception as e:
        logger.error(f"Price fetch error for {coin_id}: {e}")
        return None

def fetch_top_coins(limit: int = 20) -> List[Dict]:
    """টপ কয়েনের দাম (মার্কেট ক্যাপ অনুযায়ী)"""
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "1h",
            },
            timeout=15,
        )
        resp.raise_for_status()
        coins = resp.json()
        # BDT দাম পেতে আলাদা করে ফেচ করতে হবে (অথবা USD * exchange rate)
        # আমরা এখানে USD দাম পাবো, BDT এক্সচেঞ্জ রেট দিয়ে বের করব
        # তবে সঠিকতার জন্য আলাদা করে BDT দামও ফেচ করব
        ids = [c["id"] for c in coins]
        bdt_prices = {}
        try:
            bdt_resp = requests.get(
                f"{COINGECKO_API}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "bdt"},
                timeout=10,
            )
            bdt_resp.raise_for_status()
            bdt_data = bdt_resp.json()
            for cid, vals in bdt_data.items():
                bdt_prices[cid] = vals.get("bdt", 0)
        except:
            pass

        result = []
        for coin in coins:
            usd = coin.get("current_price", 0)
            bdt = bdt_prices.get(coin["id"], usd * 120)  # fallback approx
            result.append({
                "id": coin["id"],
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "usd": usd,
                "bdt": bdt,
                "change_1h": coin.get("price_change_percentage_1h_in_currency", 0),
            })
        return result
    except Exception as e:
        logger.error(f"Top coins fetch error: {e}")
        return []

def get_usd_bdt_rate() -> float:
    """USD থেকে BDT রেট ফেচ (ক্যাশ সহ)"""
    # tether এর দাম ব্যবহার করি
    usdt_price = fetch_live_price("tether")
    if usdt_price:
        return usdt_price[1]  # bdt per usdt
    # fallback
    return 120.0

# ========== কমান্ড হ্যান্ডলার ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    lang = get_user_language(user_id)
    # ইউজার ডাটাবেসে না থাকলে অ্যাড
    data = fetch_jsonbin_data()
    users = data.get("users", {})
    if str(user_id) not in users:
        users[str(user_id)] = {"lang": lang}
        data["users"] = users
        data["stats"]["total_users"] = len(users)
        update_jsonbin_data(data)

    welcome_text = get_string("welcome", lang)

    # চ্যাট টাইপ অনুযায়ী কিবোর্ড
    if update.effective_chat.type == "private":
        # রিপ্লাই কিবোর্ড
        keyboard = [
            [KeyboardButton("/prices"), KeyboardButton("/search")],
            [KeyboardButton("/cal"), KeyboardButton("/lang")],
            [KeyboardButton("/help"), KeyboardButton("/developer")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    else:
        # গ্রুপে ইনলাইন
        keyboard = [
            [
                InlineKeyboardButton(get_string("inline_keyboard", lang)["prices"], callback_data="prices"),
                InlineKeyboardButton(get_string("inline_keyboard", lang)["search"], switch_inline_query_current_chat=""),
            ],
            [
                InlineKeyboardButton(get_string("inline_keyboard", lang)["cal"], switch_inline_query_current_chat="/cal "),
                InlineKeyboardButton(get_string("inline_keyboard", lang)["lang"], callback_data="lang"),
            ],
            [
                InlineKeyboardButton(get_string("inline_keyboard", lang)["help"], callback_data="help"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    increment_command_stats()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    help_text = get_string("help", lang)
    await update.message.reply_text(help_text, parse_mode="Markdown")
    increment_command_stats()

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    msg = await update.message.reply_text("🔄 Fetching top cryptocurrencies...")

    top_coins = fetch_top_coins(20)
    if not top_coins:
        await msg.edit_text("❌ Failed to fetch prices. Try again later.")
        return

    header = get_string("prices_header", lang)
    lines = [header]
    for coin in top_coins:
        change = coin["change_1h"] or 0
        arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
        line = (
            f"{arrow} **{coin['name']} ({coin['symbol']})**\n"
            f"   💵 ${coin['usd']:,.4f} | ৳{coin['bdt']:,.2f}   {change:+.2f}%"
        )
        lines.append(line)

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n\n...(truncated)"

    # ইনলাইন বাটন (গ্রুপেও ইনলাইন দিব, প্রাইভেটেও দিব সুবিধার্থে)
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="prices")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    increment_command_stats()

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    args = context.args
    if not args:
        await update.message.reply_text(get_string("search_usage", lang))
        return

    query = " ".join(args)
    searching_text = get_string("searching", lang, query=query)
    msg = await update.message.reply_text(searching_text)

    coin_info = search_coin_id(query)
    if not coin_info:
        await msg.edit_text(get_string("search_not_found", lang))
        return

    coin_id = coin_info["id"]
    price = fetch_live_price(coin_id)
    if not price:
        await msg.edit_text("❌ Price fetch failed. Try again later.")
        return

    usd, bdt = price
    text = get_string(
        "search_found",
        lang,
        name=coin_info["name"],
        symbol=coin_info["symbol"].upper(),
        usd=usd,
        bdt=bdt,
        id=coin_id,
        symbol_lower=coin_info["symbol"].lower(),
    )

    keyboard = [
        [
            InlineKeyboardButton(f"💱 Convert 1 {coin_info['symbol'].upper()}", switch_inline_query_current_chat=f"/cal 1 {coin_info['symbol'].lower()} to usd"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{coin_id}"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    increment_command_stats()

async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    args = context.args
    # ফরম্যাট: /cal 100 usd to bdt  বা /cal 1 btc to usd
    if len(args) < 4:
        await update.message.reply_text(get_string("conversion_error", lang))
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return

    from_curr = args[1].lower()
    to_word = args[2].lower()
    to_curr = args[3].lower()
    if to_word != "to":
        await update.message.reply_text(get_string("conversion_error", lang))
        return

    # রেট বের করা
    # USD/BDT রেট
    usd_bdt_rate = get_usd_bdt_rate()

    # ফ্রম কারেন্সির USD ভ্যালু
    if from_curr == "usd" or from_curr == "usdt":
        from_usd_value = 1.0
    elif from_curr == "bdt":
        from_usd_value = 1.0 / usd_bdt_rate
    else:
        # ক্রিপ্টো কয়েন
        coin = search_coin_id(from_curr)
        if not coin:
            await update.message.reply_text(f"❌ Currency '{from_curr}' not recognized.")
            return
        price = fetch_live_price(coin["id"])
        if not price:
            await update.message.reply_text("❌ Failed to fetch price.")
            return
        from_usd_value = price[0]

    # টু কারেন্সির USD ভ্যালু
    if to_curr in ["usd", "usdt"]:
        to_usd_value = 1.0
    elif to_curr == "bdt":
        to_usd_value = 1.0 / usd_bdt_rate
    else:
        coin = search_coin_id(to_curr)
        if not coin:
            await update.message.reply_text(f"❌ Currency '{to_curr}' not recognized.")
            return
        price = fetch_live_price(coin["id"])
        if not price:
            await update.message.reply_text("❌ Failed to fetch price.")
            return
        to_usd_value = price[0]

    # ক্যালকুলেশন
    total_usd = amount * from_usd_value
    result = total_usd / to_usd_value

    text = get_string(
        "conversion_result",
        lang,
        amount=amount,
        from_curr=from_curr.upper(),
        result=result,
        to_curr=to_curr.upper(),
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    increment_command_stats()

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_string("lang_select", lang)

    keyboard = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"setlang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)
    increment_command_stats()

async def developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_string("developer_info", lang)
    await update.message.reply_text(text, parse_mode="Markdown")
    increment_command_stats()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    data = fetch_jsonbin_data()
    stats = data.get("stats", {})
    users = stats.get("total_users", 0)
    commands = stats.get("total_commands", 0)
    text = get_string("stats_text", lang, users=users, commands=commands)
    await update.message.reply_text(text, parse_mode="Markdown")
    increment_command_stats()

# ========== কলব্যাক হ্যান্ডলার ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_language(user_id)

    if data == "prices":
        await query.edit_message_text("🔄 Fetching...")
        top_coins = fetch_top_coins(20)
        if not top_coins:
            await query.edit_message_text("❌ Failed to fetch prices.")
            return
        header = get_string("prices_header", lang)
        lines = [header]
        for coin in top_coins:
            change = coin["change_1h"] or 0
            arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
            line = (
                f"{arrow} **{coin['name']} ({coin['symbol']})**\n"
                f"   💵 ${coin['usd']:,.4f} | ৳{coin['bdt']:,.2f}   {change:+.2f}%"
            )
            lines.append(line)
        text = "\n\n".join(lines)[:4000]
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="prices")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "lang":
        text = get_string("lang_select", lang)
        keyboard = []
        row = []
        for code, name in LANGUAGES.items():
            row.append(InlineKeyboardButton(name, callback_data=f"setlang_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "help":
        help_text = get_string("help", lang)
        await query.edit_message_text(help_text, parse_mode="Markdown")

    elif data.startswith("setlang_"):
        new_lang = data.split("_")[1]
        if new_lang in LANGUAGES:
            set_user_language(user_id, new_lang)
            lang = new_lang
            changed_text = get_string("lang_changed", lang)
            await query.edit_message_text(changed_text)

    elif data.startswith("refresh_"):
        coin_id = data.split("_", 1)[1]
        await query.edit_message_text("🔄 Refreshing...")
        price = fetch_live_price(coin_id)
        if not price:
            await query.edit_message_text("❌ Refresh failed.")
            return
        # কয়েনের নাম বের করতে হবে
        coins = fetch_coins_list()
        coin_name = coin_id
        coin_symbol = coin_id.upper()
        for c in coins:
            if c["id"] == coin_id:
                coin_name = c["name"]
                coin_symbol = c["symbol"].upper()
                break
        usd, bdt = price
        text = get_string(
            "search_found",
            lang,
            name=coin_name,
            symbol=coin_symbol,
            usd=usd,
            bdt=bdt,
            id=coin_id,
            symbol_lower=coin_symbol.lower(),
        )
        keyboard = [
            [
                InlineKeyboardButton(f"💱 Convert 1 {coin_symbol}", switch_inline_query_current_chat=f"/cal 1 {coin_symbol.lower()} to usd"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{coin_id}"),
            ],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    increment_command_stats()

# ========== ইনলাইন কোয়েরি (গ্রুপে দ্রুত সার্চ) ==========
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.inline_query.query.strip()
    if not query_text:
        return

    # /cal বা /search প্রিফিক্স চেক
    if query_text.startswith("/cal "):
        # ইনলাইন থেকে ক্যালকুলেশন
        # আমরা শুধু একটা রেজাল্ট দিব
        parts = query_text[5:].strip().split()
        if len(parts) >= 4:
            # সরলীকৃত হ্যান্ডলিং: ইউজারকে বলি /cal কমান্ড ব্যবহার করতে
            await update.inline_query.answer([])
            return

    # সাধারণ কয়েন সার্চ
    coin = search_coin_id(query_text)
    if not coin:
        await update.inline_query.answer([])
        return

    price = fetch_live_price(coin["id"])
    if not price:
        await update.inline_query.answer([])
        return

    usd, bdt = price
    lang = get_user_language(update.inline_query.from_user.id)
    title = f"{coin['name']} ({coin['symbol'].upper()})"
    description = f"💵 ${usd:,.4f} | ৳{bdt:,.2f}"
    message_text = get_string(
        "search_found",
        lang,
        name=coin["name"],
        symbol=coin["symbol"].upper(),
        usd=usd,
        bdt=bdt,
        id=coin["id"],
        symbol_lower=coin["symbol"].lower(),
    )

    from telegram import InlineQueryResultArticle, InputTextMessageContent
    result = InlineQueryResultArticle(
        id=coin["id"],
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(message_text, parse_mode="Markdown"),
        thumb_url=f"https://coinicons-api.vercel.app/api/icon/{coin['symbol'].lower()}",
    )
    await update.inline_query.answer([result], cache_time=10)

# ========== মেসেজ হ্যান্ডলার (ব্যক্তিগত চ্যাটে টেক্সট) ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # শুধু প্রাইভেট চ্যাটে রিপ্লাই কিবোর্ডের বাটন হ্যান্ডলিং
    text = update.message.text
    if text == "/prices":
        await prices_command(update, context)
    elif text == "/search":
        await update.message.reply_text("Please use: /search <coin name>")
    elif text == "/cal":
        await update.message.reply_text("Please use: /cal <amount> <from> to <to>")
    elif text == "/lang":
        await lang_command(update, context)
    elif text == "/help":
        await help_command(update, context)
    elif text == "/developer":
        await developer_command(update, context)
    elif text == "/stats":
        await stats_command(update, context)
    else:
        # অন্য মেসেজ ইগনোর
        pass

# ========== এরর হ্যান্ডলার ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ========== মেইন ==========
def main():
    # অ্যাপ্লিকেশন তৈরি
    app = Application.builder().token(BOT_TOKEN).build()

    # কমান্ড হ্যান্ডলার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("cal", cal_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("developer", developer_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # কলব্যাক
    app.add_handler(CallbackQueryHandler(button_callback))

    # ইনলাইন কোয়েরি
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ইনলাইন (গ্রুপে @bot ব্যবহার)
    from telegram.ext import InlineQueryHandler
    app.add_handler(InlineQueryHandler(inline_query))

    # এরর
    app.add_error_handler(error_handler)

    # কমান্ড সাজেশন সেট
    commands = [
        ("start", "Start the bot"),
        ("prices", "Show top 20 cryptocurrencies"),
        ("search", "Search for a coin"),
        ("cal", "Currency converter"),
        ("lang", "Change language"),
        ("developer", "Developer info"),
        ("stats", "Bot statistics"),
        ("help", "Show help"),
    ]
    # বট কমান্ড সেট করতে পারলে করা যেতে পারে
    # তবে এটা botfather দিয়ে করাই ভালো

    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
