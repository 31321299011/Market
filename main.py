#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import re
import asyncio
import threading
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any

import aiohttp
import requests  # শুধু JSONBin সিঙ্ক্রোনাস রেখেছি (বটের স্পিডে প্রভাব ফেলে না)
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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

# JSONBin কনফিগ (আগের মতো)
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# ------------------------- API এন্ডপয়েন্ট (২০+ সোর্স) -------------------------
API_SOURCES = {
    "coingecko_search": "https://api.coingecko.com/api/v3/search?query={query}",
    "coingecko_price": "https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd",
    "coingecko_markets": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false",

    "coincap_search": "https://api.coincap.io/v2/assets?search={query}&limit=1",
    "coincap_price": "https://api.coincap.io/v2/assets/{id}",
    "coincap_markets": "https://api.coincap.io/v2/assets?limit=20",

    "coinpaprika_search": "https://api.coinpaprika.com/v1/search?q={query}&c=currencies&limit=1",
    "coinpaprika_price": "https://api.coinpaprika.com/v1/tickers/{id}",
    "coinpaprika_markets": "https://api.coinpaprika.com/v1/tickers?quotes=USD&limit=20",

    "binance_ticker": "https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT",
    "binance_price": "https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT",

    "kucoin_ticker": "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}-USDT",
    "kucoin_price": "https://api.kucoin.com/api/v1/market/stats?symbol={symbol}-USDT",

    "coinbase_price": "https://api.coinbase.com/v2/prices/{id}-USD/spot",
    "coinbase_ticker": "https://api.coinbase.com/v2/prices/{id}-USD/buy",

    "cryptocompare_price": "https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD",
    "cryptocompare_markets": "https://min-api.cryptocompare.com/data/top/mktcapfull?limit=20&tsym=USD",

    "bitfinex_ticker": "https://api.bitfinex.com/v1/pubticker/{symbol}usd",
    "bitstamp_ticker": "https://www.bitstamp.net/api/v2/ticker/{symbol}usd/",
    "gemini_ticker": "https://api.gemini.com/v1/pubticker/{symbol}usd",
    "bybit_ticker": "https://api.bybit.com/v2/public/tickers?symbol={symbol}USDT",
}
FRANKFURTER_API = "https://api.frankfurter.app/latest?from=USD&to=BDT"

# ------------------------- ভাষা টেক্সট (আগের মতো) -------------------------
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

# লগিং
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------- অ্যাসিঙ্ক API হেল্পার -------------------------
async def fastest_request(session: aiohttp.ClientSession, api_calls: List[Tuple[str, str, Dict]]) -> Optional[Any]:
    """
    একাধিক API এন্ডপয়েন্টে সমান্তরাল GET রিকোয়েস্ট করে এবং প্রথম সফল JSON রেজাল্ট ফেরত দেয়।
    """
    async def fetch(method, url, params):
        try:
            if method.upper() == "GET":
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except:
            pass
        return None

    tasks = []
    for method, url_tpl, params in api_calls:
        url = url_tpl.format(**params) if params else url_tpl
        # প্যারামিটার আলাদা পাঠানো নয়, সব URL-এই এম্বেডেড (কারণ বিভিন্ন API ভিন্ন ফরম্যাট চায়)
        tasks.append(fetch(method, url, {}))

    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        result = task.result()
        if result is not None:
            return result
    return None

async def get_usd_bdt_rate() -> float:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FRANKFURTER_API, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                data = await resp.json()
                return data["rates"]["BDT"]
    except:
        return 118.0

async def search_coins(query: str) -> List[Dict]:
    # সমস্ত search endpoint ব্যবহার করি
    calls = [
        ("GET", API_SOURCES["coingecko_search"], {"query": query}),
        ("GET", API_SOURCES["coincap_search"], {"query": query}),
        ("GET", API_SOURCES["coinpaprika_search"], {"query": query}),
        # Binance-এ সরাসরি সার্চ নেই, তাই skip
        # KuCoin symbol-based, skip
        # CryptoCompare ব্যবহার করতে পারি (fsym=query, tsyms=USD) -> price endpoint
        ("GET", API_SOURCES["cryptocompare_price"], {"symbol": query.upper()}),
    ]
    async with aiohttp.ClientSession() as session:
        data = await fastest_request(session, calls)
    if not data:
        return []
    # বিভিন্ন API-র রেসপন্স পার্সিং
    if "coins" in data:  # coingecko
        return data["coins"]
    elif "data" in data and isinstance(data["data"], list):  # coincap
        assets = data["data"]
        return [{"id": a["id"], "name": a["name"], "symbol": a["symbol"]} for a in assets]
    elif "currencies" in data:  # coinpaprika
        currencies = data.get("currencies", [])
        return [{"id": c["id"], "name": c["name"], "symbol": c["symbol"]} for c in currencies]
    elif "USD" in data:  # cryptocompare price endpoint (শুধু দাম, কিন্তু আমরা সার্চ হিসেবে ধরে নিচ্ছি)
        # id বানাই symbol থেকেই
        symbol = query.upper()
        return [{"id": symbol.lower(), "name": symbol, "symbol": symbol}]
    return []

async def get_coin_price(coin_id: str) -> Optional[Dict]:
    calls = [
        ("GET", API_SOURCES["coingecko_price"], {"id": coin_id}),
        ("GET", API_SOURCES["coincap_price"], {"id": coin_id}),
        ("GET", API_SOURCES["coinpaprika_price"], {"id": coin_id}),
        ("GET", API_SOURCES["coinbase_price"], {"id": coin_id.upper()}),
        ("GET", API_SOURCES["cryptocompare_price"], {"symbol": coin_id.upper()}),
        ("GET", API_SOURCES["binance_price"], {"symbol": coin_id.upper()}),
        ("GET", API_SOURCES["kucoin_price"], {"symbol": coin_id.upper()}),
        ("GET", API_SOURCES["bitfinex_ticker"], {"symbol": coin_id.lower()}),
        ("GET", API_SOURCES["bitstamp_ticker"], {"symbol": coin_id.lower()}),
        ("GET", API_SOURCES["gemini_ticker"], {"symbol": coin_id.lower()}),
        ("GET", API_SOURCES["bybit_ticker"], {"symbol": coin_id.upper()}),
    ]
    async with aiohttp.ClientSession() as session:
        data = await fastest_request(session, calls)
    if not data:
        return None

    # বিভিন্ন সোর্স থেকে USD price extract
    if "usd" in data:  # coingecko: {"bitcoin":{"usd":...}}
        return data.get(coin_id, None)
    elif "data" in data:
        if "priceUsd" in data["data"]:
            return {"usd": float(data["data"]["priceUsd"])}
        elif "price" in data["data"]:  # coinbase: {"data":{"amount":"..."}}
            return {"usd": float(data["data"]["amount"])}
    elif "quotes" in data and "USD" in data["quotes"]:
        return {"usd": data["quotes"]["USD"]["price"]}
    elif "USD" in data:  # cryptocompare
        return {"usd": data["USD"]}
    elif "price" in data:  # binance: {"symbol":"BTCUSDT","price":"..."}
        return {"usd": float(data["price"])}
    elif "data" in data and isinstance(data["data"], dict) and "price" in data["data"]:  # kucoin
        return {"usd": float(data["data"]["price"])}
    elif "last_price" in data:  # bitfinex
        return {"usd": float(data["last_price"])}
    elif "last" in data:  # bitstamp
        return {"usd": float(data["last"])}
    elif "last" in data:  # gemini
        return {"usd": float(data["last"])}
    elif "result" in data and len(data["result"]) > 0:  # bybit
        return {"usd": float(data["result"][0]["last_price"])}
    return None

async def get_top_coins(limit: int = 20) -> List[Dict]:
    calls = [
        ("GET", API_SOURCES["coingecko_markets"], {}),
        ("GET", API_SOURCES["coincap_markets"], {}),
        ("GET", API_SOURCES["coinpaprika_markets"], {}),
        ("GET", API_SOURCES["cryptocompare_markets"], {}),
    ]
    async with aiohttp.ClientSession() as session:
        data = await fastest_request(session, calls)
    if not data:
        return []

    # coingecko format
    if isinstance(data, list) and len(data) > 0 and "current_price" in data[0]:
        return data
    # coincap
    elif "data" in data and isinstance(data["data"], list):
        assets = data["data"][:limit]
        result = []
        for a in assets:
            result.append({
                "name": a["name"],
                "symbol": a["symbol"],
                "current_price": float(a["priceUsd"]),
                "price_change_percentage_24h": float(a.get("changePercent24Hr", 0))
            })
        return result
    # coinpaprika
    elif isinstance(data, list) and len(data) > 0 and "quotes" in data[0]:
        result = []
        for ticker in data[:limit]:
            result.append({
                "name": ticker["name"],
                "symbol": ticker["symbol"],
                "current_price": ticker["quotes"]["USD"]["price"],
                "price_change_percentage_24h": ticker["quotes"]["USD"].get("percent_change_24h", 0)
            })
        return result
    # cryptocompare
    elif "Data" in data and isinstance(data["Data"], list):
        result = []
        for coin in data["Data"][:limit]:
            name = coin["CoinInfo"]["FullName"]
            symbol = coin["CoinInfo"]["Name"]
            usd = coin.get("RAW", {}).get("USD", {}).get("PRICE", 0)
            chg = coin.get("RAW", {}).get("USD", {}).get("CHANGEPCT24HOUR", 0)
            result.append({
                "name": name,
                "symbol": symbol,
                "current_price": usd,
                "price_change_percentage_24h": chg
            })
        return result
    return []

# ------------------------- JSONBin ডাটাবেজ (requests ব্যবহার, কারণ এটি স্পিড-ক্রিটিক্যাল নয়) -------------------------
def load_db() -> Dict:
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
    return db.get("users", {}).get(str(user_id), {}).get("lang", "en")

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

# ------------------------- কনভার্টার (অ্যাসিঙ্ক) -------------------------
async def convert_currency(amount: float, from_cur: str, to_cur: str) -> Optional[float]:
    from_cur = from_cur.lower()
    to_cur = to_cur.lower()
    if from_cur in ["usd", "bdt"] and to_cur in ["usd", "bdt"]:
        usd_bdt = await get_usd_bdt_rate()
        if from_cur == "usd" and to_cur == "bdt":
            return amount * usd_bdt
        elif from_cur == "bdt" and to_cur == "usd":
            return amount / usd_bdt
        else:
            return amount

    crypto_id = from_cur if from_cur not in ["usd", "bdt"] else to_cur
    coins = await search_coins(crypto_id)
    if not coins:
        return None
    coin = coins[0]
    price_data = await get_coin_price(coin["id"])
    if not price_data or "usd" not in price_data:
        return None
    usd_price = price_data["usd"]
    usd_bdt = await get_usd_bdt_rate()

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

# ------------------------- কীবোর্ড জেনারেটর (আগের মতো) -------------------------
def get_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [KeyboardButton(t["button_prices"]), KeyboardButton(t["button_search"])],
        [KeyboardButton(t["button_calc"]), KeyboardButton(t["button_lang"])],
        [KeyboardButton(t["button_help"]), KeyboardButton(t["button_dev"])],
        [KeyboardButton(t["button_stats"])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inline_menu(lang: str) -> InlineKeyboardMarkup:
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

def back_keyboard_inline(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start")]])

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ])

# ------------------------- হ্যান্ডলার (সব অ্যাসিঙ্ক) -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["welcome"], reply_markup=get_reply_keyboard(lang))
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
    coins = await get_top_coins(20)
    if not coins:
        await msg.edit_text(t["no_price"])
        return
    usd_bdt = await get_usd_bdt_rate()
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
    reply_markup = get_reply_keyboard(lang) if is_private else back_keyboard_inline(lang)
    await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    increment_command_count()

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
    if not context.args:
        await update.message.reply_text(t["search_usage"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(t["fetching"])
    coins = await search_coins(query)
    if not coins:
        await msg.edit_text(t["coin_not_found"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    coin = coins[0]
    price_data = await get_coin_price(coin["id"])
    if not price_data or "usd" not in price_data:
        await msg.edit_text(t["no_price"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    usd = price_data["usd"]
    usd_bdt = await get_usd_bdt_rate()
    bdt = usd * usd_bdt
    text = t["price_info"].format(name=coin['name'], symbol=coin['symbol'].upper(), usd=f"{usd:,.4f}", bdt=f"{bdt:,.2f}", id=coin['id'])
    text += f"\n\n💡 {t['cal_hint']}"
    keyboard = [
        [InlineKeyboardButton("🧮 Quick Convert", callback_data=f"calc_{coin['id']}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    increment_command_count()

async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    is_private = update.effective_chat.type == "private"
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(t["calc_prompt"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    text = " ".join(context.args)
    match = re.match(r"^([\d.]+)\s+(\w+)\s+to\s+(\w+)$", text, re.IGNORECASE)
    if not match:
        await update.message.reply_text(t["conversion_error"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    amount = float(match.group(1))
    from_cur = match.group(2).lower()
    to_cur = match.group(3).lower()
    msg = await update.message.reply_text(t["fetching"])
    result = await convert_currency(amount, from_cur, to_cur)
    if result is None:
        await msg.edit_text(t["conversion_error"], reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang))
        return
    to_amount = f"{result:,.8f}".rstrip('0').rstrip('.') if '.' in f"{result:,.8f}" else f"{result:,.0f}"
    text_out = t["conversion_result"].format(from_amount=f"{amount:,.4f}", from_currency=from_cur.upper(), to_amount=to_amount, to_currency=to_cur.upper())
    await msg.edit_text(text_out + f"\n\n💡 {t['cal_hint']}", reply_markup=back_keyboard_inline(lang) if not is_private else get_reply_keyboard(lang), parse_mode=ParseMode.HTML)
    increment_command_count()

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await update.message.reply_text(t["select_lang"], reply_markup=lang_keyboard())
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
    t = TEXTS[lang]
    users, commands = get_stats()
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["stats"].format(users=users, commands=commands), reply_markup=get_reply_keyboard(lang))
    else:
        await update.message.reply_text(t["stats"].format(users=users, commands=commands), reply_markup=back_keyboard_inline(lang))
    increment_command_count()

# ------------------------- ক্যালব্যাক হ্যান্ডলার -------------------------
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
        coins = await get_top_coins(20)
        if not coins:
            await query.edit_message_text(t["no_price"], reply_markup=back_keyboard_inline(lang))
            return
        usd_bdt = await get_usd_bdt_rate()
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
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard_inline(lang))
    elif data == "search_prompt":
        await query.edit_message_text(t["search_prompt"], reply_markup=back_keyboard_inline(lang))
    elif data == "calc_prompt":
        await query.edit_message_text(t["calc_prompt"], reply_markup=back_keyboard_inline(lang))
    elif data == "lang_menu":
        await query.edit_message_text(t["select_lang"], reply_markup=lang_keyboard())
    elif data == "help":
        await query.edit_message_text(t["help"], reply_markup=back_keyboard_inline(lang), parse_mode=ParseMode.HTML)
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

# ------------------------- মেসেজ হ্যান্ডলার (প্রাইভেট বাটন) -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        if text == t["button_prices"]:
            await prices_command(update, context)
        elif text == t["button_search"]:
            await update.message.reply_text(t["search_prompt"], reply_markup=get_reply_keyboard(lang))
        elif text == t["button_calc"]:
            await update.message.reply_text(t["calc_prompt"], reply_markup=get_reply_keyboard(lang))
        elif text == t["button_lang"]:
            await lang_command(update, context)
        elif text == t["button_help"]:
            await help_command(update, context)
        elif text == t["button_dev"]:
            await developer_command(update, context)
        elif text == t["button_stats"]:
            await stats_command(update, context)
        else:
            await update.message.reply_text(t["help"], reply_markup=get_reply_keyboard(lang))

# ------------------------- এরর হ্যান্ডলার -------------------------
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
    logger.info("⚡ Superfast bot started with 20+ APIs and asyncio race!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
