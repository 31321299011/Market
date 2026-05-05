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

JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

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
MINI_APP_URL = "https://31321299011.github.io/Testhtml/"

_price_cache = {}
_search_cache = {}
_rate_cache = {}
CACHE_TTL_PRICE = 30
CACHE_TTL_SEARCH = 300
CACHE_TTL_RATE = 300
_cache_lock = threading.Lock()

TEXTS = {
    "bn": {
        "welcome": "🌟 ক্রিপ্টো মার্কেট বটে স্বাগতম! 🌟\n\nলাইভ কয়েনের দাম USD ও BDT তে।",
        "help": "❓ সাহায্য\n\n/prices – শীর্ষ ২০ কয়েন\n/search <coin> – কয়েন খুঁজুন\n/cal – কনভার্টার\n/lang – ভাষা পরিবর্তন\n/developer – ডেভেলপার\n/stats – পরিসংখ্যান\n📞 সাপোর্ট: @jhgmaing",
        "fetching": "🔄 তথ্য আনা হচ্ছে...",
        "top_coins": "💰 শীর্ষ ২০ ক্রিপ্টোকারেন্সি",
        "coin_not_found": "❌ কয়েন পাওয়া যায়নি!",
        "conversion_result": "✅ {from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ ফরম্যাট: /cal 1 btc to usd",
        "lang_changed": "✅ ভাষা বাংলায় পরিবর্তিত!",
        "stats": "📊 ইউজার: {users}, কমান্ড: {commands}",
        "developer": "👨‍💻 @jhgmaing",
        "price_info": "✅ {name} ({symbol})\n💵 ${usd} | ৳{bdt}",
        "button_prices": "📊 শীর্ষ কয়েন",
        "button_search": "🔍 কয়েন খুঁজুন",
        "button_calc": "🧮 ক্যালকুলেটর",
        "button_lang": "🌐 ভাষা",
        "button_help": "❓ সাহায্য",
        "button_dev": "👤 ডেভেলপার",
        "button_stats": "📈 পরিসংখ্যান",
        "button_miniapp": "🛑 Open Mini App",
        "miniapp_msg": "👇 মিনি অ্যাপ ওপেন করতে নিচের বাটনে ক্লিক করুন"
    },
    "en": {
        "welcome": "🌟 Welcome to Crypto Market Bot! 🌟\n\nLive crypto prices in USD & BDT.",
        "help": "❓ Help\n\n/prices – Top 20\n/search <coin> – Search\n/cal – Converter\n/lang – Language\n/developer – Dev\n/stats – Stats\n📞 Support: @jhgmaing",
        "fetching": "🔄 Fetching data...",
        "top_coins": "💰 Top 20 Cryptocurrencies",
        "coin_not_found": "❌ Coin not found!",
        "conversion_result": "✅ {from_amount} {from_currency} = {to_amount} {to_currency}",
        "conversion_error": "❌ Format: /cal 1 btc to usd",
        "lang_changed": "✅ Language changed to English!",
        "stats": "📊 Users: {users}, Commands: {commands}",
        "developer": "👨‍💻 @jhgmaing",
        "price_info": "✅ {name} ({symbol})\n💵 ${usd} | ৳{bdt}",
        "button_prices": "📊 Top Coins",
        "button_search": "🔍 Search Coin",
        "button_calc": "🧮 Calculator",
        "button_lang": "🌐 Language",
        "button_help": "❓ Help",
        "button_dev": "👤 Developer",
        "button_stats": "📈 Statistics",
        "button_miniapp": "🛑 Open Mini App",
        "miniapp_msg": "👇 Click the button below to open Mini App"
    }
}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def fastest_request(api_calls):
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

def get_usd_bdt_rate():
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

def search_coins(query):
    q = query.lower().strip()
    now = time.time()
    with _cache_lock:
        if q in _search_cache and (now - _search_cache[q][1]) < CACHE_TTL_SEARCH:
            return _search_cache[q][0]
    calls = [
        ("GET", API_SOURCES["coingecko"]["search"].format(query=q), {}),
        ("GET", API_SOURCES["coincap"]["search"].format(query=q), {}),
        ("GET", API_SOURCES["coinpaprika"]["search"].format(query=q), {}),
    ]
    data = fastest_request(calls)
    coins = []
    if data:
        if "coins" in data:
            coins = data["coins"]
        elif "data" in data:
            coins = [{"id": a["id"], "name": a["name"], "symbol": a["symbol"]} for a in data.get("data", [])]
        elif "currencies" in data:
            coins = [{"id": c["id"], "name": c["name"], "symbol": c["symbol"]} for c in data.get("currencies", [])]
    with _cache_lock:
        _search_cache[q] = (coins, now)
    return coins

def get_coin_price(coin_id):
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

def get_top_coins(limit=20):
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
        for a in data["data"][:limit]:
            result.append({"name": a["name"], "symbol": a["symbol"], "current_price": float(a["priceUsd"]), "price_change_percentage_24h": float(a.get("changePercent24Hr", 0))})
    elif isinstance(data, list) and data[0].get("quotes"):
        for t in data[:limit]:
            result.append({"name": t["name"], "symbol": t["symbol"], "current_price": t["quotes"]["USD"]["price"], "price_change_percentage_24h": t["quotes"]["USD"].get("percent_change_24h", 0)})
    if result:
        with _cache_lock:
            _price_cache["__top20__"] = (result, now)
    return result

def load_db():
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "X-Access-Key": JSONBIN_ACCESS_KEY}
    try:
        resp = requests.get(JSONBIN_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("record", {})
    except Exception as e:
        logger.error(f"DB load error: {e}")
        return {"users": {}, "stats": {"total_users": 0, "total_commands": 0}}

def save_db(data):
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "X-Access-Key": JSONBIN_ACCESS_KEY, "Content-Type": "application/json"}
    try:
        requests.put(JSONBIN_URL, headers=headers, json=data, timeout=10)
        return True
    except Exception as e:
        logger.error(f"DB save error: {e}")
        return False

def get_user_lang(user_id):
    db = load_db()
    return db.get("users", {}).get(str(user_id), {}).get("lang", "bn")

def set_user_lang(user_id, lang):
    db = load_db()
    if "users" not in db: db["users"] = {}
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"lang": lang, "first_seen": datetime.utcnow().isoformat()}
        db["stats"]["total_users"] = db["stats"].get("total_users", 0) + 1
    else:
        db["users"][str(user_id)]["lang"] = lang
    save_db(db)

def inc_cmd():
    db = load_db()
    db["stats"]["total_commands"] = db["stats"].get("total_commands", 0) + 1
    save_db(db)

def get_stats():
    db = load_db()
    return db["stats"].get("total_users", 0), db["stats"].get("total_commands", 0)

async def convert_currency(amount, frm, to):
    frm, to = frm.lower(), to.lower()
    if frm in ("usd","bdt") and to in ("usd","bdt"):
        rate = get_usd_bdt_rate()
        if frm=="usd" and to=="bdt": return amount*rate
        if frm=="bdt" and to=="usd": return amount/rate
        return amount
    coin_id = frm if frm not in ("usd","bdt") else to
    coins = search_coins(coin_id)
    if not coins: return None
    price = get_coin_price(coins[0]["id"])
    if not price or "usd" not in price: return None
    usd = price["usd"]
    rate = get_usd_bdt_rate()
    if frm==coin_id and to=="usd": return amount*usd
    if frm==coin_id and to=="bdt": return amount*usd*rate
    if frm=="usd" and to==coin_id: return amount/usd if usd else None
    if frm=="bdt" and to==coin_id:
        usd_amt = amount/rate
        return usd_amt/usd if usd else None
    return None

def get_reply_keyboard(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔴 "+t["button_prices"]), KeyboardButton("🟢 "+t["button_search"])],
        [KeyboardButton("🟡 "+t["button_calc"]), KeyboardButton("🔵 "+t["button_lang"])],
        [KeyboardButton("🟣 "+t["button_help"]), KeyboardButton("🟠 "+t["button_dev"])],
        [KeyboardButton("⚪ "+t["button_stats"])]
    ], resize_keyboard=True)

def get_inline_menu(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 "+t["button_prices"], callback_data="prices"),
         InlineKeyboardButton("🟢 "+t["button_search"], callback_data="search_prompt")],
        [InlineKeyboardButton("🟡 "+t["button_calc"], callback_data="calc_prompt")],
        [InlineKeyboardButton("🔵 "+t["button_lang"], callback_data="lang_menu"),
         InlineKeyboardButton("🟣 "+t["button_help"], callback_data="help")],
        [InlineKeyboardButton("🟠 "+t["button_dev"], callback_data="developer"),
         InlineKeyboardButton("⚪ "+t["button_stats"], callback_data="stats")],
        [InlineKeyboardButton("🛑 Open Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start")]])

def lang_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        await update.message.reply_text(t["welcome"], reply_markup=get_reply_keyboard(lang))
        await update.message.reply_text(t["miniapp_msg"], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Open Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]]))
    else:
        await update.message.reply_text(t["welcome"], reply_markup=get_inline_menu(lang))
    inc_cmd()

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    t = TEXTS[lang]
    await update.message.reply_text(t["help"], reply_markup=back_btn())
    inc_cmd()

async def prices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    msg = await update.message.reply_text(t["fetching"])
    coins = get_top_coins(20)
    if not coins:
        await msg.edit_text(t["coin_not_found"])
        return
    rate = get_usd_bdt_rate()
    txt = f"<b>{t['top_coins']}</b>\n"
    for c in coins:
        usd = c['current_price']
        bdt = usd*rate
        ch = c.get('price_change_percentage_24h',0)
        arrow = "📈" if ch>=0 else "📉"
        txt += f"{arrow} <b>{c['name']} ({c['symbol'].upper()})</b>\n   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {ch:+.2f}%\n"
    await msg.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=get_reply_keyboard(lang) if update.effective_chat.type=="private" else back_btn())
    inc_cmd()

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if not context.args:
        await update.message.reply_text(t["search_usage"])
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(t["fetching"])
    coins = search_coins(query)
    if not coins:
        await msg.edit_text(t["coin_not_found"]); return
    c = coins[0]
    price = get_coin_price(c['id'])
    if not price or "usd" not in price:
        await msg.edit_text(t["coin_not_found"]); return
    usd = price["usd"]
    bdt = usd * get_usd_bdt_rate()
    txt = t["price_info"].format(name=c['name'], symbol=c['symbol'].upper(), usd=f"{usd:,.4f}", bdt=f"{bdt:,.2f}")
    await msg.edit_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧮 Quick Convert", callback_data=f"calc_{c['id']}")], [InlineKeyboardButton("⬅️ Back", callback_data="start")]]))
    inc_cmd()

async def cal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    if not context.args or len(context.args)<4:
        await update.message.reply_text(t["conversion_error"]); return
    txt = " ".join(context.args)
    match = re.match(r"^([\d.]+)\s+(\w+)\s+to\s+(\w+)$", txt, re.I)
    if not match:
        await update.message.reply_text(t["conversion_error"]); return
    amount = float(match.group(1))
    frm = match.group(2).lower()
    to = match.group(3).lower()
    msg = await update.message.reply_text(t["fetching"])
    res = await convert_currency(amount, frm, to)
    if res is None:
        await msg.edit_text(t["conversion_error"]); return
    to_str = f"{res:,.8f}".rstrip('0').rstrip('.') if '.' in f"{res:,.8f}" else f"{res:,.0f}"
    out = t["conversion_result"].format(from_amount=amount, from_currency=frm.upper(), to_amount=to_str, to_currency=to.upper())
    await msg.edit_text(out)
    inc_cmd()

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(TEXTS[lang]["button_lang"], reply_markup=lang_menu())
    inc_cmd()

async def dev_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(TEXTS[lang]["developer"], reply_markup=back_btn())
    inc_cmd()

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(update.effective_user.id)
    u, c = get_stats()
    await update.message.reply_text(TEXTS[lang]["stats"].format(users=u, commands=c), reply_markup=back_btn())
    inc_cmd()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    if data == "start":
        await query.edit_message_text(t["welcome"], reply_markup=get_inline_menu(lang))
    elif data == "prices":
        coins = get_top_coins(20)
        if not coins:
            await query.edit_message_text(t["coin_not_found"]); return
        rate = get_usd_bdt_rate()
        txt = f"<b>{t['top_coins']}</b>\n"
        for c in coins:
            usd = c['current_price']; bdt = usd*rate
            ch = c.get('price_change_percentage_24h',0)
            arrow = "📈" if ch>=0 else "📉"
            txt += f"{arrow} <b>{c['name']} ({c['symbol'].upper()})</b>\n   💵 ${usd:,.4f} | ৳{bdt:,.2f}   {ch:+.2f}%\n"
        await query.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=back_btn())
    elif data == "search_prompt":
        await query.edit_message_text(t["search_usage"], reply_markup=back_btn())
    elif data == "calc_prompt":
        await query.edit_message_text(t["conversion_error"], reply_markup=back_btn())
    elif data == "lang_menu":
        await query.edit_message_text("🌍", reply_markup=lang_menu())
    elif data == "help":
        await query.edit_message_text(t["help"], reply_markup=back_btn())
    elif data == "developer":
        await query.edit_message_text(t["developer"], reply_markup=back_btn())
    elif data == "stats":
        u, c = get_stats()
        await query.edit_message_text(t["stats"].format(users=u, commands=c), reply_markup=back_btn())
    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_user_lang(user_id, new_lang)
        await query.edit_message_text(TEXTS[new_lang]["lang_changed"], reply_markup=get_inline_menu(new_lang))
    elif data.startswith("calc_"):
        coin_id = data.replace("calc_", "")
        await query.edit_message_text(f"🧮 /cal 1 {coin_id} to usd", reply_markup=back_btn())
    else:
        await query.edit_message_text(t["coin_not_found"], reply_markup=back_btn())

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = update.message.text
    t = TEXTS[lang]
    if update.effective_chat.type == "private":
        if text == "🔴 " + t["button_prices"]: await prices_cmd(update, context)
        elif text == "🟢 " + t["button_search"]: await update.message.reply_text(t["search_usage"])
        elif text == "🟡 " + t["button_calc"]: await update.message.reply_text(t["conversion_error"])
        elif text == "🔵 " + t["button_lang"]: await lang_cmd(update, context)
        elif text == "🟣 " + t["button_help"]: await help_cmd(update, context)
        elif text == "🟠 " + t["button_dev"]: await dev_cmd(update, context)
        elif text == "⚪ " + t["button_stats"]: await stats_cmd(update, context)
        else: await update.message.reply_text(t["help"])
    else:
        await update.message.reply_text(t["help"])

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception:", exc_info=context.error)

flask_app = Flask(__name__)
@flask_app.route('/health')
def health(): return 'OK', 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("prices", prices_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("cal", cal_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("developer", dev_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.add_error_handler(error_handler)
    logger.info("Colorful bot with Mini App started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
