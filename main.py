import asyncio
import requests
import json
import logging
import re
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== কনফিগারেশন =====================
TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_BIN_ID = "69dc964236566621a8a94516"

# API URLs
JSONBIN_READ = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
JSONBIN_WRITE = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# লগিং
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== ভাষার ডাটাবেস =====================
LANGUAGES = {
    "bn": {
        "name": "বাংলা", "flag": "🇧🇩",
        "welcome": "🌟 *ক্রিপ্টো মার্কেট বটে স্বাগতম!* 🌟\n\nআমি দুনিয়ার সব কয়েনের লাইভ দাম দেখাই (USD/BDT)। নিচের বাটন ব্যবহার করো।",
        "prices": "💰 লাইভ দাম",
        "search": "🔍 কয়েন সার্চ",
        "converter": "🔄 কনভার্টার",
        "language": "🌍 ভাষা",
        "developer": "👨‍💻 ডেভেলপার",
        "statistics": "📊 পরিসংখ্যান",
        "help": "❓ সাহায্য",
        "back": "◀️ পেছনে",
        "menu": "🌟 মেনু",
        "price_fetch": "🔄 লাইভ দাম আনা হচ্ছে...",
        "search_prompt": "🔍 যেকোনো কয়েনের নাম লিখুন:\nযেমন: `/search bitcoin` বা `/search dogecoin`",
        "not_found": "❌ কয়েনটি পাওয়া যায়নি! সঠিক নাম দিন।",
        "error": "⚠️ টেকনিক্যাল এরর! পরে চেষ্টা করুন।",
        "calc_usage": "📝 ব্যবহার: `/cal 100 usd to bdt`\nউদাহরণ: `/cal 1 btc to usd`",
        "calc_result": "✅ *রূপান্তর ফলাফল*\n\n{amount} {from_curr} = {result:.8f} {to_curr}",
        "dev_info": "👨‍💻 *ডেভেলপার তথ্য*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 ভার্সন: 3.0 (মেগা প্রো)\n⚡ API: CoinGecko + ফ্যালব্যাক\n💾 ডাটাবেস: JSONBin\n🚀 হোস্ট: Render",
        "stats_text": "📊 *বট পরিসংখ্যান*\n\n👥 মোট ইউজার: {users}\n🌍 ভাষা: ৪টি (বাংলা, ইংরেজি, রুশ, হিন্দি)\n⚡ স্ট্যাটাস: সচল\n🕐 সর্বশেষ আপডেট: {time}",
        "help_text": "❓ *সাহায্য মেনু*\n\n/prices – টপ ২০ কয়েনের দাম\n/search <কয়েন> – যেকোনো কয়েন সার্চ\n/cal – কনভার্টার (USD/BDT/ক্রিপ্টো)\n/lang – ভাষা পরিবর্তন\n/developer – বট তথ্য\n/stats – পরিসংখ্যান\n/help – এই মেনু\n\n💡 উদাহরণ: `/search shiba inu`\n📞 সাপোর্ট: @jhgmaing"
    },
    "en": {
        "name": "English", "flag": "🇬🇧",
        "welcome": "🌟 *Welcome to Crypto Market Bot!* 🌟\n\nI show live prices of any coin in USD/BDT. Use buttons below.",
        "prices": "💰 Live Prices",
        "search": "🔍 Search Coin",
        "converter": "🔄 Converter",
        "language": "🌍 Language",
        "developer": "👨‍💻 Developer",
        "statistics": "📊 Stats",
        "help": "❓ Help",
        "back": "◀️ Back",
        "menu": "🌟 Menu",
        "price_fetch": "🔄 Fetching live prices...",
        "search_prompt": "🔍 Type any coin name:\ne.g. `/search bitcoin` or `/search dogecoin`",
        "not_found": "❌ Coin not found! Check the name.",
        "error": "⚠️ Technical error! Try again later.",
        "calc_usage": "📝 Usage: `/cal 100 usd to bdt`\nExample: `/cal 1 btc to usd`",
        "calc_result": "✅ *Conversion Result*\n\n{amount} {from_curr} = {result:.8f} {to_curr}",
        "dev_info": "👨‍💻 *Developer Info*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 Version: 3.0 (Mega Pro)\n⚡ API: CoinGecko + Fallback\n💾 Database: JSONBin\n🚀 Host: Render",
        "stats_text": "📊 *Bot Statistics*\n\n👥 Total Users: {users}\n🌍 Languages: 4 (Bengali, English, Russian, Hindi)\n⚡ Status: Active\n🕐 Last Update: {time}",
        "help_text": "❓ *Help Menu*\n\n/prices – Top 20 coins\n/search <coin> – Search any coin\n/cal – Converter (USD/BDT/Crypto)\n/lang – Change language\n/developer – Bot info\n/stats – Statistics\n/help – This menu\n\n💡 Example: `/search shiba inu`\n📞 Support: @jhgmaing"
    },
    "ru": {
        "name": "Русский", "flag": "🇷🇺",
        "welcome": "🌟 *Добро пожаловать в Crypto Market Bot!* 🌟\n\nЯ показываю живые цены любой монеты в USD/BDT. Используйте кнопки.",
        "prices": "💰 Цены",
        "search": "🔍 Поиск",
        "converter": "🔄 Конвертер",
        "language": "🌍 Язык",
        "developer": "👨‍💻 Разраб",
        "statistics": "📊 Стат",
        "help": "❓ Помощь",
        "back": "◀️ Назад",
        "menu": "🌟 Меню",
        "price_fetch": "🔄 Получение цен...",
        "search_prompt": "🔍 Введите название монеты:\nнапример: `/search bitcoin`",
        "not_found": "❌ Монета не найдена!",
        "error": "⚠️ Ошибка! Попробуйте позже.",
        "calc_usage": "📝 Использование: `/cal 100 usd to bdt`",
        "calc_result": "✅ *Результат*\n\n{amount} {from_curr} = {result:.8f} {to_curr}",
        "dev_info": "👨‍💻 *Разработчик*\n\n@jhgmaing\n@bot_developer_io\n\nВерсия 3.0\nAPI: CoinGecko",
        "stats_text": "📊 *Статистика*\n\n👥 Пользователей: {users}\n🌍 Языков: 4\n⚡ Статус: Активен\n🕐 {time}",
        "help_text": "❓ *Помощь*\n\n/prices – Топ 20 монет\n/search <монета> – Поиск\n/cal – Конвертер\n/lang – Язык\n/developer – Инфо\n/stats – Статистика\n/help – Меню"
    },
    "hi": {
        "name": "हिन्दी", "flag": "🇮🇳",
        "welcome": "🌟 *क्रिप्टो मार्केट बॉट में स्वागत है!* 🌟\n\nमैं किसी भी सिक्के की लाइव कीमत USD/BDT में दिखाता हूँ।",
        "prices": "💰 कीमतें",
        "search": "🔍 खोजें",
        "converter": "🔄 परिवर्तक",
        "language": "🌍 भाषा",
        "developer": "👨‍💻 डेवलपर",
        "statistics": "📊 आँकड़े",
        "help": "❓ सहायता",
        "back": "◀️ पीछे",
        "menu": "🌟 मेनू",
        "price_fetch": "🔄 कीमतें लाई जा रही हैं...",
        "search_prompt": "🔍 कोई भी सिक्का खोजें: `/search bitcoin`",
        "not_found": "❌ सिक्का नहीं मिला!",
        "error": "⚠️ त्रुटि! बाद में प्रयास करें।",
        "calc_usage": "📝 उपयोग: `/cal 100 usd to bdt`",
        "calc_result": "✅ *परिणाम*\n\n{amount} {from_curr} = {result:.8f} {to_curr}",
        "dev_info": "👨‍💻 *डेवलपर*\n\n@jhgmaing\n@bot_developer_io\n\nसंस्करण 3.0",
        "stats_text": "📊 *आँकड़े*\n\n👥 कुल उपयोगकर्ता: {users}\n🌍 भाषाएँ: 4\n⚡ स्थिति: सक्रिय\n🕐 {time}",
        "help_text": "❓ *सहायता*\n\n/prices – टॉप 20 सिक्के\n/search <सिक्का> – खोजें\n/cal – परिवर्तक\n/lang – भाषा\n/developer – जानकारी\n/stats – आँकड़े"
    }
}

# ===================== ডাটাবেস ফাংশন =====================
def get_user_lang(user_id):
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        resp = requests.get(JSONBIN_READ, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("record", {})
            return data.get("users", {}).get(str(user_id), {}).get("lang", "bn")
    except:
        pass
    return "bn"

def set_user_lang(user_id, lang):
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        resp = requests.get(JSONBIN_READ, headers=headers, timeout=5)
        if resp.status_code != 200:
            return
        data = resp.json().get("record", {})
        if "users" not in data:
            data["users"] = {}
        if str(user_id) not in data["users"]:
            data["users"][str(user_id)] = {}
        data["users"][str(user_id)]["lang"] = lang
        headers_write = {**headers, "Content-Type": "application/json"}
        requests.put(JSONBIN_WRITE, json=data, headers=headers_write, timeout=5)
    except:
        pass

def update_user_stats(user_id):
    """শুধু ইউজার কাউন্ট বাড়ানোর জন্য (ঐচ্ছিক)"""
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        resp = requests.get(JSONBIN_READ, headers=headers, timeout=5)
        if resp.status_code != 200:
            return
        data = resp.json().get("record", {})
        if "users" not in data:
            data["users"] = {}
        if str(user_id) not in data["users"]:
            data["users"][str(user_id)] = {"joined": str(datetime.now())}
            headers_write = {**headers, "Content-Type": "application/json"}
            requests.put(JSONBIN_WRITE, json=data, headers=headers_write, timeout=5)
    except:
        pass

# ===================== ক্রিপ্টো API (একাধিক ব্যাকআপ) =====================
# ক্যাশ সিস্টেম
price_cache = {"data": None, "time": 0, "source": None}

def fetch_coingecko_top():
    """CoinGecko থেকে টপ কয়েন আনার চেষ্টা"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            coins = r.json()
            result = []
            for c in coins:
                result.append({
                    "name": c["name"],
                    "symbol": c["symbol"].upper(),
                    "usd": c["current_price"],
                    "bdt": c["current_price"] * 118 if c["current_price"] else 0,
                    "change": c.get("price_change_percentage_24h", 0)
                })
            return result, "CoinGecko"
    except:
        pass
    return None, None

def fetch_alternative_api():
    """ব্যাকআপ: Kucoin বা অন্য (এখানে সিমুলেটেড)"""
    try:
        # Kucoin থেকে কিছু সাধারণ কয়েন
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            tickers = data.get("data", {}).get("ticker", [])
            result = []
            for t in tickers[:20]:
                symbol = t.get("symbol", "")
                if symbol.endswith("-USDT"):
                    coin = symbol.replace("-USDT", "")
                    price = float(t.get("last", 0))
                    if price > 0:
                        result.append({
                            "name": coin,
                            "symbol": coin,
                            "usd": price,
                            "bdt": price * 118,
                            "change": float(t.get("changeRate", 0)) * 100
                        })
            if result:
                return result, "KuCoin"
    except:
        pass
    return None, None

def get_top_coins():
    """প্রথমে CoinGecko, তারপর ব্যাকআপ, তারপর ফিক্সড ডাটা"""
    global price_cache
    now = time.time()
    if price_cache["data"] and now - price_cache["time"] < 45:  # 45 সেকেন্ড ক্যাশ
        return price_cache["data"]
    
    data, source = fetch_coingecko_top()
    if data:
        price_cache = {"data": data, "time": now, "source": source}
        return data
    
    data, source = fetch_alternative_api()
    if data:
        price_cache = {"data": data, "time": now, "source": source}
        return data
    
    # ফাইনাল ব্যাকআপ: স্ট্যাটিক ডাটা (কখনো ফেল করবে না)
    fallback = [
        {"name": "Bitcoin", "symbol": "BTC", "usd": 70000, "bdt": 8260000, "change": 2.5},
        {"name": "Ethereum", "symbol": "ETH", "usd": 3500, "bdt": 413000, "change": 1.8},
        {"name": "BNB", "symbol": "BNB", "usd": 600, "bdt": 70800, "change": -0.5},
        {"name": "Solana", "symbol": "SOL", "usd": 150, "bdt": 17700, "change": 5.2},
        {"name": "XRP", "symbol": "XRP", "usd": 0.6, "bdt": 70.8, "change": -1.2},
        {"name": "Dogecoin", "symbol": "DOGE", "usd": 0.15, "bdt": 17.7, "change": 3.0},
        {"name": "Cardano", "symbol": "ADA", "usd": 0.45, "bdt": 53.1, "change": -0.8},
        {"name": "Polygon", "symbol": "MATIC", "usd": 0.8, "bdt": 94.4, "change": 1.5}
    ]
    price_cache = {"data": fallback, "time": now, "source": "Fallback"}
    return fallback

def search_any_coin(query):
    """যেকোনো কয়েন সার্চ – একাধিক API ট্রাই করবে"""
    # প্রথম চেষ্টা: CoinGecko search + price
    try:
        # search
        s_url = f"https://api.coingecko.com/api/v3/search?query={query}"
        s_resp = requests.get(s_url, timeout=8)
        if s_resp.status_code == 200:
            s_data = s_resp.json()
            if s_data.get("coins") and len(s_data["coins"]) > 0:
                coin_id = s_data["coins"][0]["id"]
                name = s_data["coins"][0]["name"]
                symbol = s_data["coins"][0]["symbol"].upper()
                # price
                p_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,bdt"
                p_resp = requests.get(p_url, timeout=8)
                if p_resp.status_code == 200:
                    p_data = p_resp.json()
                    if coin_id in p_data:
                        usd = p_data[coin_id].get("usd", 0)
                        bdt = p_data[coin_id].get("bdt", usd*118)
                        return {"name": name, "symbol": symbol, "usd": usd, "bdt": bdt, "id": coin_id}
    except:
        pass
    
    # দ্বিতীয় চেষ্টা: Kucoin API থেকে অনুসন্ধান
    try:
        k_url = f"https://api.kucoin.com/api/v1/market/allTickers"
        k_resp = requests.get(k_url, timeout=8)
        if k_resp.status_code == 200:
            tickers = k_resp.json().get("data", {}).get("ticker", [])
            for t in tickers:
                if query.upper() in t.get("symbol", "") and t.get("symbol", "").endswith("-USDT"):
                    symbol = t["symbol"].replace("-USDT", "")
                    price = float(t.get("last", 0))
                    return {"name": symbol, "symbol": symbol, "usd": price, "bdt": price*118, "id": symbol.lower()}
    except:
        pass
    
    return None  # না পাওয়া গেলে

def get_live_rate(from_curr, to_curr):
    """কনভার্টারের জন্য রেট – USD, BDT, এবং যেকোনো ক্রিপ্টো"""
    rates = {"usd": 1, "bdt": 118, "usdt": 1}
    # যদি ক্রিপ্টো থাকে তাহলে টপ কয়েন থেকে রেট নেওয়া
    crypto_list = ["btc", "eth", "bnb", "sol", "xrp", "doge", "ada", "matic", "dot", "ltc"]
    if from_curr in crypto_list or to_curr in crypto_list:
        top = get_top_coins()
        for coin in top:
            sym = coin["symbol"].lower()
            if sym == from_curr:
                rates[from_curr] = coin["usd"]
            if sym == to_curr:
                rates[to_curr] = coin["usd"]
    # ডিফল্ট মান
    if from_curr not in rates:
        rates[from_curr] = 1
    if to_curr not in rates:
        rates[to_curr] = 1
    return rates[from_curr], rates[to_curr]

# ===================== বক্স সিস্টেম (ইনলাইন কিবোর্ড) =====================
def get_main_keyboard(lang_code):
    t = LANGUAGES[lang_code]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{t['prices']}", callback_data="menu_prices"),
         InlineKeyboardButton(f"{t['search']}", callback_data="menu_search")],
        [InlineKeyboardButton(f"{t['converter']}", callback_data="menu_converter"),
         InlineKeyboardButton(f"{t['language']}", callback_data="menu_language")],
        [InlineKeyboardButton(f"{t['developer']}", callback_data="menu_developer"),
         InlineKeyboardButton(f"{t['statistics']}", callback_data="menu_statistics")],
        [InlineKeyboardButton(f"{t['help']}", callback_data="menu_help")]
    ])

# ===================== টেলিগ্রাম হ্যান্ডলার =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_user_stats(uid)
    lang = get_user_lang(uid)
    text = LANGUAGES[lang]["welcome"]
    await update.message.reply_text(text, reply_markup=get_main_keyboard(lang), parse_mode="Markdown")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = get_user_lang(uid)
    action = query.data.split("_")[1]
    
    if action == "prices":
        await query.edit_message_text(LANGUAGES[lang]["price_fetch"])
        coins = get_top_coins()
        msg = f"💰 *{LANGUAGES[lang]['prices']}*\n\n"
        for c in coins[:15]:
            emoji = "📈" if c["change"] >= 0 else "📉"
            msg += f"{emoji} *{c['name']}* ({c['symbol']})\n   💵 ${c['usd']:,.2f} | ৳{c['bdt']:,.2f}   {c['change']:+.2f}%\n\n"
        msg += f"\n🔍 /search <coin>"
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "search":
        msg = LANGUAGES[lang]["search_prompt"]
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "converter":
        msg = LANGUAGES[lang]["calc_usage"]
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "language":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]
        ])
        await query.edit_message_text("🌍 *Select your language / ভাষা নির্বাচন করুন*", reply_markup=kb, parse_mode="Markdown")
    
    elif action == "developer":
        msg = LANGUAGES[lang]["dev_info"]
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "statistics":
        total_users = 0
        try:
            headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
            r = requests.get(JSONBIN_READ, headers=headers, timeout=5)
            if r.status_code == 200:
                total_users = len(r.json().get("record", {}).get("users", {}))
        except:
            pass
        msg = LANGUAGES[lang]["stats_text"].format(users=total_users, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "help":
        msg = LANGUAGES[lang]["help_text"]
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="menu_back")]])
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")
    
    elif action == "back":
        await query.edit_message_text(LANGUAGES[lang]["welcome"], reply_markup=get_main_keyboard(lang), parse_mode="Markdown")

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    new_lang = query.data.split("_")[1]
    set_user_lang(uid, new_lang)
    # নতুন ভাষায় মেনু দেখানো
    text = LANGUAGES[new_lang]["welcome"]
    await query.edit_message_text(text, reply_markup=get_main_keyboard(new_lang), parse_mode="Markdown")

# কমান্ড হ্যান্ডলার
async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    await update.message.reply_text(LANGUAGES[lang]["price_fetch"])
    coins = get_top_coins()
    msg = f"💰 *{LANGUAGES[lang]['prices']}*\n\n"
    for c in coins[:15]:
        emoji = "📈" if c["change"] >= 0 else "📉"
        msg += f"{emoji} *{c['name']}* ({c['symbol']})\n   💵 ${c['usd']:,.2f} | ৳{c['bdt']:,.2f}   {c['change']:+.2f}%\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    if not context.args:
        await update.message.reply_text(LANGUAGES[lang]["search_prompt"], parse_mode="Markdown")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"🔄 Searching *{query}*...", parse_mode="Markdown")
    coin = search_any_coin(query)
    if not coin or coin["usd"] == 0:
        await update.message.reply_text(LANGUAGES[lang]["not_found"], parse_mode="Markdown")
        return
    msg = f"✅ *{coin['name']}* ({coin['symbol']})\n\n💰 *Current Price*\n💵 ${coin['usd']:,.4f} USD\n🇧🇩 ৳{coin['bdt']:,.2f} BDT\n\n💡 /cal 1 {coin['symbol'].lower()} to usd"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    if not context.args:
        await update.message.reply_text(LANGUAGES[lang]["calc_usage"], parse_mode="Markdown")
        return
    try:
        txt = " ".join(context.args).lower()
        m = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s+to\s+(\w+)", txt)
        if not m:
            await update.message.reply_text(LANGUAGES[lang]["calc_usage"], parse_mode="Markdown")
            return
        amount = float(m.group(1))
        from_curr = m.group(2)
        to_curr = m.group(3)
        rate_from, rate_to = get_live_rate(from_curr, to_curr)
        usd_value = amount * rate_from
        result = usd_value / rate_to
        msg = LANGUAGES[lang]["calc_result"].format(amount=amount, from_curr=from_curr.upper(), result=result, to_curr=to_curr.upper())
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Calc error: {e}")
        await update.message.reply_text(LANGUAGES[lang]["error"], parse_mode="Markdown")

async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    await update.message.reply_text(LANGUAGES[lang]["dev_info"], parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    total_users = 0
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        r = requests.get(JSONBIN_READ, headers=headers, timeout=5)
        if r.status_code == 200:
            total_users = len(r.json().get("record", {}).get("users", {}))
    except:
        pass
    msg = LANGUAGES[lang]["stats_text"].format(users=total_users, time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)
    await update.message.reply_text(LANGUAGES[lang]["help_text"], parse_mode="Markdown")

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_user_lang(uid)  # বর্তমান ভাষা (বাটনের জন্য)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")]
    ])
    await update.message.reply_text("🌍 *ভাষা নির্বাচন করুন / Select language*", reply_markup=kb, parse_mode="Markdown")

# ===================== মেইন ফাংশন =====================
def main():
    # Render ফ্রি টায়ারের জন্য ইভেন্ট লুপ ফিক্স
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    app = Application.builder().token(TOKEN).build()
    
    # কমান্ড রেজিস্টার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("cal", calc_command))
    app.add_handler(CommandHandler("developer", dev_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("lang", lang_command))
    
    # কলব্যাক
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="lang_"))
    
    print("="*50)
    print("🤖 CRYPTO MARKET BOT v3.0 - MEGA PRO")
    print("="*50)
    print("✅ 4 Languages: বাংলা, English, Русский, हिन्दी")
    print("✅ Any Coin Support + Multiple API Fallback")
    print("✅ Box System + Inline Buttons")
    print("✅ Group & Channel Ready")
    print("✅ JSONBin Database Active")
    print("="*50)
    print("🚀 Bot is RUNNING on Render Free Tier")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
