#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import re
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from functools import lru_cache

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# ========== কনফিগারেশন ==========
BOT_TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"

# JSONBin.io কনফিগ (পাবলিক বিন)
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# কয়েনগেকো API (ফ্রি টিয়ার)
COINGECKO_API = "https://api.coingecko.com/api/v3"

# ক্যাশ টাইম
CACHE_SECONDS = 180  # ৩ মিনিট
COINS_LIST_CACHE_SECONDS = 7200  # ২ ঘন্টা

# ভাষা সমর্থন
LANGUAGES = {
    "en": "English",
    "bn": "বাংলা",
    "ru": "Русский",
    "hi": "हिन्दी",
}
DEFAULT_LANG = "en"

# ডেভেলপার ইউজারনেম
DEVELOPERS = ["@jhgmaing", "@bot_developer_io"]

# ========== গ্লোবাল ক্যাশ ==========
_price_cache = {}
_coins_list_cache = None
_coins_list_time = None
_cache_lock = threading.RLock()

# ========== লগিং ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== JSONBin হেল্পার (ত্রুটি সহনশীল) ==========
def fetch_jsonbin_data():
    """JSONBin থেকে ডেটা আনা, ব্যর্থ হলে ডিফল্ট স্ট্রাকচার"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
    }
    try:
        resp = requests.get(JSONBIN_URL, headers=headers, timeout=8)
        resp.raise_for_status()
        return resp.json().get("record", {})
    except Exception as e:
        logger.warning(f"JSONBin fetch failed: {e}")
        return {"users": {}, "languages": list(LANGUAGES.keys()), "stats": {"total_users": 0, "total_commands": 0}}

def update_jsonbin_data(record):
    """JSONBin আপডেট, ব্যর্থ হলে শুধু লগ"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "X-Access-Key": JSONBIN_ACCESS_KEY,
        "Content-Type": "application/json",
    }
    try:
        requests.put(JSONBIN_URL, headers=headers, json=record, timeout=8)
    except Exception as e:
        logger.error(f"JSONBin update failed: {e}")

def get_user_lang(user_id):
    data = fetch_jsonbin_data()
    return data.get("users", {}).get(str(user_id), {}).get("lang", DEFAULT_LANG)

def set_user_lang(user_id, lang):
    data = fetch_jsonbin_data()
    users = data.get("users", {})
    uid = str(user_id)
    if uid not in users:
        users[uid] = {}
    users[uid]["lang"] = lang
    data["users"] = users
    data["stats"]["total_users"] = len(users)
    update_jsonbin_data(data)

def inc_command_stat():
    try:
        data = fetch_jsonbin_data()
        data["stats"]["total_commands"] = data.get("stats", {}).get("total_commands", 0) + 1
        update_jsonbin_data(data)
    except:
        pass

# ========== স্ট্রিং লোকালাইজেশন ==========
STR = {
    "welcome": {
        "en": "🌟 Welcome to Crypto Market Bot! 🌟\n\nI show live prices of any coin in USD/BDT.\nUse /help for commands.",
        "bn": "🌟 ক্রিপ্টো মার্কেট বটে স্বাগতম! 🌟\n\nআমি যেকোনো কয়েনের লাইভ মূল্য USD/BDT তে দেখাই।\nকমান্ডের জন্য /help ব্যবহার করুন।",
        "ru": "🌟 Добро пожаловать в Crypto Market Bot! 🌟\n\nЯ показываю живые цены любой монеты в USD/BDT.\nИспользуйте /help для команд.",
        "hi": "🌟 क्रिप्टो मार्केट बॉट में स्वागत है! 🌟\n\nमैं किसी भी सिक्के की लाइव कीमत USD/BDT में दिखाता हूँ।\nकमांड के लिए /help का उपयोग करें।",
    },
    "help": {
        "en": (
            "❓ **Help Menu**\n\n"
            "/prices – Top 20 coins\n"
            "/search <coin> – Search any coin\n"
            "/cal – Currency converter\n"
            "/lang – Change language\n"
            "/developer – Bot info\n"
            "/stats – Statistics\n"
            "/help – This menu\n\n"
            "💡 Support: @jhgmaing"
        ),
        "bn": (
            "❓ **সাহায্য মেনু**\n\n"
            "/prices – শীর্ষ ২০ কয়েন\n"
            "/search <কয়েন> – যেকোনো কয়েন সার্চ\n"
            "/cal – কারেন্সি কনভার্টার\n"
            "/lang – ভাষা পরিবর্তন\n"
            "/developer – বট তথ্য\n"
            "/stats – পরিসংখ্যান\n"
            "/help – এই মেনু\n\n"
            "💡 সাপোর্ট: @jhgmaing"
        ),
        "ru": (
            "❓ **Меню справки**\n\n"
            "/prices – Топ 20 монет\n"
            "/search <монета> – Поиск монеты\n"
            "/cal – Конвертер валют\n"
            "/lang – Сменить язык\n"
            "/developer – Информация о боте\n"
            "/stats – Статистика\n"
            "/help – Это меню\n\n"
            "💡 Поддержка: @jhgmaing"
        ),
        "hi": (
            "❓ **सहायता मेनू**\n\n"
            "/prices – शीर्ष 20 सिक्के\n"
            "/search <सिक्का> – कोई भी सिक्का खोजें\n"
            "/cal – मुद्रा परिवर्तक\n"
            "/lang – भाषा बदलें\n"
            "/developer – बॉट जानकारी\n"
            "/stats – आंकड़े\n"
            "/help – यह मेनू\n\n"
            "💡 सहायता: @jhgmaing"
        ),
    },
    "search_found": {
        "en": "✅ **{name} ({symbol})**\n\n📈 Current Price:\n💵 USD: ${usd:,.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 Market Info:\n🆔 ID: {id}\n🕐 Updated: Just now\n\n💡 Commands:\n/cal 1 {sym_low} to usd\n/cal 100 usd to {sym_low}",
        "bn": "✅ **{name} ({symbol})**\n\n📈 বর্তমান মূল্য:\n💵 USD: ${usd:,.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 বাজার তথ্য:\n🆔 আইডি: {id}\n🕐 আপডেট: এইমাত্র\n\n💡 কমান্ড:\n/cal 1 {sym_low} to usd\n/cal 100 usd to {sym_low}",
        "ru": "✅ **{name} ({symbol})**\n\n📈 Текущая цена:\n💵 USD: ${usd:,.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 Информация:\n🆔 ID: {id}\n🕐 Обновлено: Только что\n\n💡 Команды:\n/cal 1 {sym_low} to usd\n/cal 100 usd to {sym_low}",
        "hi": "✅ **{name} ({symbol})**\n\n📈 वर्तमान मूल्य:\n💵 USD: ${usd:,.4f}\n🇧🇩 BDT: ৳{bdt:,.2f}\n\n📊 बाजार जानकारी:\n🆔 ID: {id}\n🕐 अपडेट किया गया: अभी\n\n💡 कमांड:\n/cal 1 {sym_low} to usd\n/cal 100 usd to {sym_low}",
    },
    "search_not_found": {
        "en": "❌ Coin not found! Please check the name.\nExample: /search bitcoin",
        "bn": "❌ কয়েন পাওয়া যায়নি! নামটি যাচাই করুন।\nউদাহরণ: /search bitcoin",
        "ru": "❌ Монета не найдена! Проверьте название.\nПример: /search bitcoin",
        "hi": "❌ सिक्का नहीं मिला! कृपया नाम जांचें।\nउदाहरण: /search bitcoin",
    },
    "conversion_result": {
        "en": "✅ **Conversion Result**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "bn": "✅ **রূপান্তর ফলাফল**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "ru": "✅ **Результат конвертации**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
        "hi": "✅ **रूपांतरण परिणाम**\n\n{amount:,.4f} {from_curr} = {result:,.4f} {to_curr}",
    },
    "lang_select": {
        "en": "🌍 Select language:",
        "bn": "🌍 ভাষা নির্বাচন করুন:",
        "ru": "🌍 Выберите язык:",
        "hi": "🌍 भाषा चुनें:",
    },
    "lang_changed": {
        "en": "✅ Language changed to English!",
        "bn": "✅ ভাষা পরিবর্তন করে বাংলা করা হয়েছে!",
        "ru": "✅ Язык изменён на Русский!",
        "hi": "✅ भाषा बदलकर हिन्दी कर दी गई है!",
    },
    "developer": {
        "en": "👨‍💻 **Developer Info**\n\nBot created by:\n• @jhgmaing\n• @bot_developer_io\n\nVersion: 2.0.1\nUpdates: Real-time crypto prices",
        "bn": "👨‍💻 **ডেভেলপার তথ্য**\n\nবট তৈরি করেছেন:\n• @jhgmaing\n• @bot_developer_io\n\nভার্সন: 2.0.1\nআপডেট: রিয়েল-টাইম ক্রিপ্টো মূল্য",
        "ru": "👨‍💻 **Информация о разработчике**\n\nБот создан:\n• @jhgmaing\n• @bot_developer_io\n\nВерсия: 2.0.1\nОбновления: Реальные цены",
        "hi": "👨‍💻 **डेवलपर जानकारी**\n\nबॉट द्वारा बनाया गया:\n• @jhgmaing\n• @bot_developer_io\n\nसंस्करण: 2.0.1\nअपडेट: रियल-टाइम क्रिप्टो कीमतें",
    },
    "stats": {
        "en": "📊 **Bot Statistics**\n\n👥 Total Users: {users}\n🔄 Total Commands: {commands}",
        "bn": "📊 **বট পরিসংখ্যান**\n\n👥 মোট ব্যবহারকারী: {users}\n🔄 মোট কমান্ড: {commands}",
        "ru": "📊 **Статистика бота**\n\n👥 Всего пользователей: {users}\n🔄 Всего команд: {commands}",
        "hi": "📊 **बॉट आंकड़े**\n\n👥 कुल उपयोगकर्ता: {users}\n🔄 कुल कमांड: {commands}",
    },
}

def t(key, lang, **kwargs):
    txt = STR.get(key, {}).get(lang, STR[key].get("en", key))
    if kwargs:
        try:
            return txt.format(**kwargs)
        except:
            return txt
    return txt

# ========== CoinGecko API হেল্পার (ক্যাশিং সহ) ==========
def _fetch_coins_list():
    global _coins_list_cache, _coins_list_time
    with _cache_lock:
        now = datetime.now()
        if _coins_list_cache and _coins_list_time and (now - _coins_list_time).seconds < COINS_LIST_CACHE_SECONDS:
            return _coins_list_cache
    try:
        resp = requests.get(f"{COINGECKO_API}/coins/list", timeout=15)
        resp.raise_for_status()
        coins = resp.json()
        with _cache_lock:
            _coins_list_cache = coins
            _coins_list_time = now
        return coins
    except Exception as e:
        logger.error(f"Coins list fetch error: {e}")
        return _coins_list_cache or []

def search_coin(query):
    """কয়েনের নাম/সিম্বল থেকে ID বের করা (উন্নত ম্যাচিং)"""
    coins = _fetch_coins_list()
    if not coins:
        return None
    q = query.lower().strip()
    # 1) exact symbol
    for c in coins:
        if c.get("symbol", "").lower() == q:
            return c
    # 2) exact name
    for c in coins:
        if c.get("name", "").lower() == q:
            return c
    # 3) symbol starts with
    for c in coins:
        if c.get("symbol", "").lower().startswith(q):
            return c
    # 4) name starts with
    for c in coins:
        if c.get("name", "").lower().startswith(q):
            return c
    # 5) contains in name
    for c in coins:
        if q in c.get("name", "").lower():
            return c
    return None

def get_price(coin_id):
    """একটি কয়েনের USD ও BDT দাম (ক্যাশ সহ)"""
    with _cache_lock:
        if coin_id in _price_cache:
            usd, bdt, ts = _price_cache[coin_id]
            if (datetime.now() - ts).seconds < CACHE_SECONDS:
                return usd, bdt
    try:
        resp = requests.get(
            f"{COINGECKO_API}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd,bdt"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json().get(coin_id, {})
        usd = data.get("usd")
        bdt = data.get("bdt")
        if usd is not None and bdt is not None:
            with _cache_lock:
                _price_cache[coin_id] = (usd, bdt, datetime.now())
            return usd, bdt
    except Exception as e:
        logger.error(f"Price fetch error for {coin_id}: {e}")
    return None, None

def get_top_coins(limit=20):
    """মার্কেট ক্যাপ অনুযায়ী টপ কয়েনের দাম"""
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "price_change_percentage": "1h",
            },
            timeout=15
        )
        resp.raise_for_status()
        coins = resp.json()
        ids = [c["id"] for c in coins]
        # BDT দাম আলাদাভাবে আনা
        bdt_prices = {}
        if ids:
            bdt_resp = requests.get(
                f"{COINGECKO_API}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "bdt"},
                timeout=10
            )
            if bdt_resp.status_code == 200:
                bdt_prices = bdt_resp.json()
        result = []
        usd_bdt_rate = get_usd_bdt_rate()
        for c in coins:
            usd = c["current_price"]
            bdt = bdt_prices.get(c["id"], {}).get("bdt")
            if bdt is None:
                bdt = usd * usd_bdt_rate
            result.append({
                "id": c["id"],
                "symbol": c["symbol"].upper(),
                "name": c["name"],
                "usd": usd,
                "bdt": bdt,
                "change": c.get("price_change_percentage_1h_in_currency", 0)
            })
        return result
    except Exception as e:
        logger.error(f"Top coins error: {e}")
        return []

def get_usd_bdt_rate():
    """USDT এর BDT দাম থেকে রেট আনা (স্থিতিশীল)"""
    usdt_usd, usdt_bdt = get_price("tether")
    if usdt_usd and usdt_bdt:
        return usdt_bdt / usdt_usd
    return 120.0  # ফলব্যাক

# ========== টেলিগ্রাম হ্যান্ডলার ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    # ইউজার সংরক্ষণ
    data = fetch_jsonbin_data()
    if str(user.id) not in data.get("users", {}):
        users = data.get("users", {})
        users[str(user.id)] = {"lang": lang}
        data["users"] = users
        data["stats"]["total_users"] = len(users)
        update_jsonbin_data(data)

    welcome = t("welcome", lang)
    if update.effective_chat.type == "private":
        kb = [
            [KeyboardButton("/prices"), KeyboardButton("/search")],
            [KeyboardButton("/cal"), KeyboardButton("/lang")],
            [KeyboardButton("/help"), KeyboardButton("/developer")],
        ]
        markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    else:
        markup = None
    await update.message.reply_text(welcome, reply_markup=markup)
    inc_command_stat()

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(t("help", lang), parse_mode="Markdown")
    inc_command_stat()

async def prices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    msg = await update.message.reply_text("🔄 Fetching top cryptocurrencies...")
    coins = get_top_coins(20)
    if not coins:
        await msg.edit_text("❌ Failed to fetch prices. Try again later.")
        return
    lines = [f"💰 **Live Prices**\n"]
    for c in coins:
        ch = c["change"] or 0
        arrow = "📈" if ch > 0 else "📉" if ch < 0 else "➖"
        lines.append(
            f"{arrow} **{c['name']} ({c['symbol']})**\n"
            f"   💵 ${c['usd']:,.4f} | ৳{c['bdt']:,.2f}   {ch:+.2f}%"
        )
    text = "\n\n".join(lines)[:4096]
    kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="prices")]]
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    inc_command_stat()

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("🔍 Usage: /search bitcoin")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔄 Searching {query}...")
    coin = search_coin(query)
    if not coin:
        await msg.edit_text(t("search_not_found", lang))
        return
    usd, bdt = get_price(coin["id"])
    if usd is None:
        await msg.edit_text("❌ Price fetch failed.")
        return
    text = t("search_found", lang,
             name=coin["name"], symbol=coin["symbol"].upper(),
             usd=usd, bdt=bdt, id=coin["id"], sym_low=coin["symbol"].lower())
    kb = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{coin['id']}")]]
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    inc_command_stat()

async def cal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    args = context.args
    if len(args) < 4:
        await update.message.reply_text("ℹ️ Usage: /cal 100 usd to bdt")
        return
    try:
        amount = float(args[0])
        from_cur = args[1].lower()
        to_word = args[2].lower()
        to_cur = args[3].lower()
        if to_word != "to":
            raise ValueError
    except:
        await update.message.reply_text("❌ Invalid format. Example: /cal 1 btc to usd")
        return

    # রেট সংগ্রহ
    usd_bdt = get_usd_bdt_rate()
    def to_usd(sym):
        if sym in ("usd", "usdt"): return 1.0
        if sym == "bdt": return 1.0 / usd_bdt
        coin = search_coin(sym)
        if not coin: return None
        p, _ = get_price(coin["id"])
        return p
    from_usd = to_usd(from_cur)
    to_usd_val = to_usd(to_cur)
    if from_usd is None or to_usd_val is None or to_usd_val == 0:
        await update.message.reply_text("❌ Invalid currency.")
        return
    result = amount * from_usd / to_usd_val
    text = t("conversion_result", lang, amount=amount, from_curr=from_cur.upper(), result=result, to_curr=to_cur.upper())
    await update.message.reply_text(text, parse_mode="Markdown")
    inc_command_stat()

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    kb = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"setlang_{code}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    await update.message.reply_text(t("lang_select", lang), reply_markup=InlineKeyboardMarkup(kb))
    inc_command_stat()

async def developer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(t("developer", lang), parse_mode="Markdown")
    inc_command_stat()

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    data = fetch_jsonbin_data()
    users = data.get("stats", {}).get("total_users", 0)
    commands = data.get("stats", {}).get("total_commands", 0)
    await update.message.reply_text(t("stats", lang, users=users, commands=commands), parse_mode="Markdown")
    inc_command_stat()

# ========== কলব্যাক হ্যান্ডলার ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)

    if data == "prices":
        await query.edit_message_text("🔄 Fetching...")
        coins = get_top_coins(20)
        if not coins:
            await query.edit_message_text("❌ Failed to fetch.")
            return
        lines = ["💰 **Live Prices**\n"]
        for c in coins:
            ch = c["change"] or 0
            arrow = "📈" if ch > 0 else "📉" if ch < 0 else "➖"
            lines.append(f"{arrow} **{c['name']} ({c['symbol']})**\n   💵 ${c['usd']:,.4f} | ৳{c['bdt']:,.2f}   {ch:+.2f}%")
        text = "\n\n".join(lines)[:4096]
        kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="prices")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("setlang_"):
        new_lang = data.split("_")[1]
        if new_lang in LANGUAGES:
            set_user_lang(user_id, new_lang)
            await query.edit_message_text(t("lang_changed", new_lang))

    elif data.startswith("refresh_"):
        coin_id = data.split("_", 1)[1]
        await query.edit_message_text("🔄 Refreshing...")
        usd, bdt = get_price(coin_id)
        if usd is None:
            await query.edit_message_text("❌ Refresh failed.")
            return
        coins = _fetch_coins_list()
        coin_info = next((c for c in coins if c["id"] == coin_id), {"name": coin_id, "symbol": coin_id})
        text = t("search_found", lang,
                 name=coin_info["name"], symbol=coin_info["symbol"].upper(),
                 usd=usd, bdt=bdt, id=coin_id, sym_low=coin_info["symbol"].lower())
        kb = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{coin_id}")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    inc_command_stat()

# ========== ইনলাইন কোয়েরি (গ্রুপে @market_bajar_bot ...) ==========
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query.strip()
    if not q:
        return
    lang = get_user_lang(update.inline_query.from_user.id)
    coin = search_coin(q)
    if not coin:
        await update.inline_query.answer([])
        return
    usd, bdt = get_price(coin["id"])
    if usd is None:
        await update.inline_query.answer([])
        return
    title = f"{coin['name']} ({coin['symbol'].upper()})"
    desc = f"💵 ${usd:,.4f} | ৳{bdt:,.2f}"
    msg_text = t("search_found", lang,
                 name=coin["name"], symbol=coin["symbol"].upper(),
                 usd=usd, bdt=bdt, id=coin["id"], sym_low=coin["symbol"].lower())
    from telegram import InlineQueryResultArticle, InputTextMessageContent
    result = InlineQueryResultArticle(
        id=coin["id"],
        title=title,
        description=desc,
        input_message_content=InputTextMessageContent(msg_text, parse_mode="Markdown"),
        thumb_url=f"https://coinicons-api.vercel.app/api/icon/{coin['symbol'].lower()}"
    )
    await update.inline_query.answer([result], cache_time=10)

# ========== মেসেজ হ্যান্ডলার (প্রাইভেট চ্যাট বাটন) ==========
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/prices":
        await prices_cmd(update, context)
    elif text == "/search":
        await update.message.reply_text("ℹ️ Usage: /search bitcoin")
    elif text == "/cal":
        await update.message.reply_text("ℹ️ Usage: /cal 1 btc to usd")
    elif text == "/lang":
        await lang_cmd(update, context)
    elif text == "/help":
        await help_cmd(update, context)
    elif text == "/developer":
        await developer_cmd(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception:", exc_info=context.error)

# ========== মেইন ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("prices", prices_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("cal", cal_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("developer", developer_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
