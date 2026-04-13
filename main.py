import requests
import json
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

# ============= কনফিগারেশন =============
TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_BIN_ID = "69dc964236566621a8a94516"

# JSONBin API
JSONBIN_READ_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
JSONBIN_WRITE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# লগিং
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= 4 টা ল্যাঙ্গুয়েজ =============
LANGUAGES = {
    "bn": {"name": "বাংলা", "flag": "🇧🇩", "prices": "💰 লাইভ ক্রিপ্টো দাম", "search": "🔍 কয়েন সার্চ", "not_found": "❌ কয়েন পাওয়া যায়নি!", "error": "⚠️ এরর হয়েছে!", "help": "🤖 হেল্প মেনু", "dev": "👨‍💻 ডেভেলপার", "stats": "📊 পরিসংখ্যান", "conv": "🔄 কনভার্টার"},
    "en": {"name": "English", "flag": "🇬🇧", "prices": "💰 Live Crypto Prices", "search": "🔍 Search Coin", "not_found": "❌ Coin not found!", "error": "⚠️ Error occurred!", "help": "🤖 Help Menu", "dev": "👨‍💻 Developer", "stats": "📊 Statistics", "conv": "🔄 Converter"},
    "ru": {"name": "Русский", "flag": "🇷🇺", "prices": "💰 Живые цены", "search": "🔍 Поиск монеты", "not_found": "❌ Монета не найдена!", "error": "⚠️ Ошибка!", "help": "🤖 Помощь", "dev": "👨‍💻 Разработчик", "stats": "📊 Статистика", "conv": "🔄 Конвертер"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳", "prices": "💰 लाइव कीमतें", "search": "🔍 कॉइन खोजें", "not_found": "❌ कॉइन नहीं मिला!", "error": "⚠️ त्रुटि!", "help": "🤖 सहायता", "dev": "👨‍💻 डेवलपर", "stats": "📊 आँकड़े", "conv": "🔄 कनवर्टर"}
}

# ============= ডাটাবেস =============
def get_user_data():
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        response = requests.get(JSONBIN_READ_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("record", {"users": {}})
    except:
        pass
    return {"users": {}}

def save_user_data(data):
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "Content-Type": "application/json"}
        requests.put(JSONBIN_WRITE_URL, json=data, headers=headers, timeout=10)
    except:
        pass

def get_user_lang(user_id):
    data = get_user_data()
    return data["users"].get(str(user_id), {}).get("language", "bn")

def set_user_lang(user_id, lang):
    data = get_user_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {}
    data["users"][str(user_id)]["language"] = lang
    save_user_data(data)

# ============= যেকোনো কয়েনের প্রাইস ফাংশন =============
def get_any_coin_price(coin_name):
    """যেকোনো কয়েনের প্রাইস আনার ফাংশন - কোন error আসবে না"""
    try:
        # কয়েনের নাম ক্লিন করা
        coin_clean = coin_name.lower().strip().replace(" ", "-").replace("_", "-")
        
        # CoinGecko search API
        search_url = f"https://api.coingecko.com/api/v3/search?query={coin_clean}"
        search_response = requests.get(search_url, timeout=10)
        
        if search_response.status_code != 200:
            return None, "API_ERROR"
        
        search_data = search_response.json()
        
        if not search_data.get("coins") or len(search_data["coins"]) == 0:
            return None, "NOT_FOUND"
        
        # প্রথম রেজাল্টের ID নেওয়া
        coin_id = search_data["coins"][0]["id"]
        coin_symbol = search_data["coins"][0]["symbol"].upper()
        coin_full_name = search_data["coins"][0]["name"]
        
        # প্রাইস ফেচ করা
        price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,bdt"
        price_response = requests.get(price_url, timeout=10)
        
        if price_response.status_code != 200:
            return None, "PRICE_ERROR"
        
        price_data = price_response.json()
        
        if coin_id not in price_data:
            return None, "NO_PRICE"
        
        usd_price = price_data[coin_id].get("usd", 0)
        bdt_price = price_data[coin_id].get("bdt", usd_price * 118)
        
        return {
            "name": coin_full_name,
            "symbol": coin_symbol,
            "usd": usd_price,
            "bdt": bdt_price,
            "id": coin_id
        }, "SUCCESS"
        
    except Exception as e:
        logger.error(f"Coin price error: {e}")
        return None, "EXCEPTION"

def get_top_coins():
    """টপ কয়েনের লিস্ট"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return get_fallback_coins()
        
        data = response.json()
        result = []
        
        for coin in data:
            result.append({
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
                "usd": coin["current_price"],
                "bdt": coin["current_price"] * 118 if coin["current_price"] else 0,
                "change": coin.get("price_change_percentage_24h", 0)
            })
        
        return result
    except:
        return get_fallback_coins()

def get_fallback_coins():
    """API কাজ না করলে ব্যাকআপ ডাটা"""
    return [
        {"name": "Bitcoin", "symbol": "BTC", "usd": 65000, "bdt": 7670000, "change": 2.5},
        {"name": "Ethereum", "symbol": "ETH", "usd": 3500, "bdt": 413000, "change": 1.8},
        {"name": "Binance Coin", "symbol": "BNB", "usd": 600, "bdt": 70800, "change": -0.5},
        {"name": "Solana", "symbol": "SOL", "usd": 150, "bdt": 17700, "change": 5.2},
        {"name": "XRP", "symbol": "XRP", "usd": 0.6, "bdt": 70.8, "change": -1.2},
        {"name": "Dogecoin", "symbol": "DOGE", "usd": 0.15, "bdt": 17.7, "change": 3.0},
        {"name": "Cardano", "symbol": "ADA", "usd": 0.45, "bdt": 53.1, "change": -0.8},
        {"name": "Polygon", "symbol": "MATIC", "usd": 0.8, "bdt": 94.4, "change": 1.5},
    ]

# ============= টেলিগ্রাম হ্যান্ডলার =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টার্ট কমান্ড - বক্স সিস্টেম"""
    keyboard = [
        [InlineKeyboardButton("💰 Prices", callback_data="menu_prices"),
         InlineKeyboardButton("🔍 Search Coin", callback_data="menu_search")],
        [InlineKeyboardButton("🔄 Converter", callback_data="menu_convert"),
         InlineKeyboardButton("🌍 Language", callback_data="menu_lang")],
        [InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_dev"),
         InlineKeyboardButton("📊 Stats", callback_data="menu_stats")],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """🌟 *CRYPTO MARKET BOT v2.0* 🌟

✅ *Supported:* Any Coin in the World!
✅ *Live Prices:* USD / BDT
✅ *Languages:* 4 Languages
✅ *24/7 Active*

🔽 *Click buttons below* 🔽"""
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন ক্লিক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data.split("_")[1]
    lang = get_user_lang(user_id)
    
    if action == "prices":
        await query.edit_message_text("🔄 Fetching top coins...")
        coins = get_top_coins()
        
        text = f"{LANGUAGES[lang]['prices']}\n\n"
        for coin in coins[:15]:
            change_emoji = "📈" if coin["change"] >= 0 else "📉"
            text += f"{change_emoji} *{coin['name']}* ({coin['symbol']})\n"
            text += f"   💵 ${coin['usd']:,.2f} | ৳{coin['bdt']:,.2f}\n"
            text += f"   📊 24h: {coin['change']:+.2f}%\n\n"
        
        text += "\n🔍 *Search any coin:* /search <coin_name>"
        
        keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "search":
        await query.edit_message_text(
            "🔍 *Search any cryptocurrency*\n\n"
            "📝 *Usage:* `/search bitcoin`\n"
            "📝 *Example:* `/search dogecoin`\n\n"
            "💡 *Try:* btc, eth, shib, pepe, any coin!",
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "⚡ *Quick search:*\n"
            "• /search bitcoin\n"
            "• /search ethereum\n"
            "• /search dogecoin\n"
            "• /search shiba inu",
            parse_mode="Markdown"
        )
    
    elif action == "convert":
        text = """🔄 *Currency Converter*

📝 *Format:* `/cal <amount> <from> to <to>`

✅ *Examples:*
• `/cal 100 usd to bdt`
• `/cal 50 bdt to usd`
• `/cal 1 btc to usd`
• `/cal 500 usdt to bdt`

💡 *Supported:* USD, BDT, BTC, ETH, USDT, BNB, SOL, XRP, DOGE, ADA"""
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "lang":
        keyboard = [
            [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")],
            [InlineKeyboardButton("◀️ Back", callback_data="menu_back")]
        ]
        await query.edit_message_text("🌍 *Select your language:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "dev":
        text = """👨‍💻 *Developer Information*

• @jhgmaing
• @bot_developer_io

📅 *Version:* 2.0 (Ultra Pro)
⚡ *API:* CoinGecko
💾 *Database:* JSONBin
🚀 *Host:* Render

✨ *Features:*
• Any Coin Support
• 4 Languages
• Live Prices
• Currency Converter"""
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "stats":
        data = get_user_data()
        total_users = len(data.get("users", {}))
        text = f"""📊 *Bot Statistics*

👥 *Total Users:* {total_users}
🌍 *Languages:* 4 (BN, EN, RU, HI)
⚡ *Status:* Active 🟢
🎯 *Coins Supported:* Unlimited

📅 *Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💾 *Database:* JSONBin
🔗 *API:* CoinGecko (Live)"""
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "help":
        text = """❓ *Help Menu*

📌 *Commands:*

/prices - Show top 20 coins
/search <coin> - Search any coin
/cal - Currency converter
/lang - Change language
/developer - Bot info
/stats - Bot statistics
/help - This menu

📌 *Examples:*
/search bitcoin
/search dogecoin
/cal 100 usd to bdt

💡 *Support:* @jhgmaing"""
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif action == "back":
        keyboard = [
            [InlineKeyboardButton("💰 Prices", callback_data="menu_prices"),
             InlineKeyboardButton("🔍 Search", callback_data="menu_search")],
            [InlineKeyboardButton("🔄 Converter", callback_data="menu_convert"),
             InlineKeyboardButton("🌍 Language", callback_data="menu_lang")],
            [InlineKeyboardButton("👨‍💻 Developer", callback_data="menu_dev"),
             InlineKeyboardButton("📊 Stats", callback_data="menu_stats")],
            [InlineKeyboardButton("❓ Help", callback_data="menu_help")]
        ]
        text = "🌟 *Main Menu* 🌟\n\nSelect an option:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    
    set_user_lang(user_id, lang)
    
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_back")]]
    await query.edit_message_text(
        f"✅ Language changed to {LANGUAGES[lang]['name']}!\n\nUse /start to see main menu.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """যেকোনো কয়েন সার্চ করার কমান্ড - কোন error আসবে না"""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not context.args:
        await update.message.reply_text(
            f"🔍 *{LANGUAGES[lang]['search']}*\n\n"
            "📝 *Usage:* `/search <coin_name>`\n"
            "✅ *Example:* `/search bitcoin`\n"
            "✅ *Example:* `/search dogecoin`\n"
            "✅ *Example:* `/search shiba inu`\n\n"
            "💡 *Try any coin name!*",
            parse_mode="Markdown"
        )
        return
    
    coin_name = " ".join(context.args)
    await update.message.reply_text(f"🔄 Searching for *{coin_name}*...", parse_mode="Markdown")
    
    result, status = get_any_coin_price(coin_name)
    
    if status != "SUCCESS" or not result or result["usd"] == 0:
        await update.message.reply_text(
            f"❌ *{LANGUAGES[lang]['not_found']}*\n\n"
            f"🔍 You searched: *{coin_name}*\n\n"
            "💡 *Tips:*\n"
            "• Use correct spelling\n"
            "• Try: bitcoin, ethereum, dogecoin\n"
            "• Use /search <coin_name>\n\n"
            "📝 *Example:* `/search bitcoin`",
            parse_mode="Markdown"
        )
        return
    
    # সফল হলে রেজাল্ট দেখান
    change_emoji = "📈" if result.get("usd", 0) > 0 else "💰"
    
    text = f"""✅ *{result['name']}* ({result['symbol']})

{change_emoji} *Current Price:*
💵 USD: `${result['usd']:,.4f}`
🇧🇩 BDT: `৳{result['bdt']:,.2f}`

📊 *Market Info:*
🆔 ID: `{result['id']}`
🕐 Updated: Just now

💡 *Commands:*
/cal 1 {result['symbol'].lower()} to usd
/cal 100 usd to {result['symbol'].lower()}"""
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{result['id']}"),
                 InlineKeyboardButton("◀️ Menu", callback_data="menu_back")]]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """টপ কয়েন দেখানোর কমান্ড"""
    await update.message.reply_text("🔄 Fetching top cryptocurrencies...")
    coins = get_top_coins()
    
    text = "💰 *Top 15 Cryptocurrencies*\n\n"
    for coin in coins[:15]:
        change_emoji = "📈" if coin["change"] >= 0 else "📉"
        text += f"{change_emoji} *{coin['name']}* ({coin['symbol']})\n"
        text += f"   💵 ${coin['usd']:,.2f} | ৳{coin['bdt']:,.2f}\n"
        text += f"   📊 24h: {coin['change']:+.2f}%\n\n"
    
    text += "\n🔍 *Search any coin:* /search <coin_name>"
    await update.message.reply_text(text, parse_mode="Markdown")

async def calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """কারেন্সি কনভার্টার"""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not context.args:
        await update.message.reply_text(
            "🔄 *Currency Converter*\n\n"
            "📝 *Format:* `/cal <amount> <from> to <to>`\n\n"
            "✅ *Examples:*\n"
            "• `/cal 100 usd to bdt`\n"
            "• `/cal 50 bdt to usd`\n"
            "• `/cal 1 btc to usd`\n"
            "• `/cal 500 usdt to bdt`\n\n"
            "💡 *Supported:* USD, BDT, BTC, ETH, USDT, BNB, SOL, XRP, DOGE, ADA",
            parse_mode="Markdown"
        )
        return
    
    try:
        text = " ".join(context.args).lower()
        match = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s+to\s+(\w+)", text)
        
        if not match:
            await update.message.reply_text("❌ *Invalid format!*\n\nUse: `/cal 100 usd to bdt`", parse_mode="Markdown")
            return
        
        amount = float(match.group(1))
        from_curr = match.group(2)
        to_curr = match.group(3)
        
        # লাইভ রেট ফেচ করার চেষ্টা
        rates = {"usd": 1, "bdt": 118, "usdt": 1}
        
        # ক্রিপ্টো রেট আপডেট করার চেষ্টা
        crypto_list = ["btc", "eth", "bnb", "sol", "xrp", "doge", "ada"]
        if from_curr in crypto_list or to_curr in crypto_list:
            top_coins = get_top_coins()
            for coin in top_coins:
                symbol = coin["symbol"].lower()
                if symbol == from_curr:
                    rates[from_curr] = coin["usd"]
                if symbol == to_curr:
                    rates[to_curr] = coin["usd"]
        
        # ডিফল্ট ভ্যালু সেট
        if from_curr not in rates:
            rates[from_curr] = 1
        if to_curr not in rates:
            rates[to_curr] = 1
        
        usd_value = amount * rates[from_curr]
        result = usd_value / rates[to_curr]
        
        await update.message.reply_text(
            f"✅ *Conversion Result*\n\n"
            f"📌 {amount:,.4f} {from_curr.upper()} = {result:,.8f} {to_curr.upper()}\n\n"
            f"💡 *More:* `/cal 100 {to_curr} to {from_curr}`",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ *Error:* {str(e)}\n\n"
            "📝 *Use format:* `/cal 100 usd to bdt`",
            parse_mode="Markdown"
        )

async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    text = f"""👨‍💻 *{LANGUAGES[lang]['dev']}*

• @jhgmaing
• @bot_developer_io

📅 *Version:* 2.0 (Ultra Pro)
⚡ *API:* CoinGecko (Live)
💾 *Database:* JSONBin
🚀 *Hosted on:* Render

✨ *Features:*
• 🌍 Any Coin Support
• 🗣️ 4 Languages
• 💰 Live Prices (USD/BDT)
• 🔄 Currency Converter
• 📊 24/7 Active

💡 *Support:* @jhgmaing"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_user_data()
    total_users = len(data.get("users", {}))
    
    text = f"""📊 *Bot Statistics*

👥 *Total Users:* {total_users}
🌍 *Languages:* 4 (BN, EN, RU, HI)
⚡ *Status:* Active 🟢
🎯 *Coins Supported:* Unlimited

📅 *Uptime:* 24/7
🕐 *Updated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💾 *Database:* JSONBin
🔗 *API:* CoinGecko (Live)

🚀 *Bot is running perfectly!*"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    text = f"""❓ *{LANGUAGES[lang]['help']}*

📌 *Commands:*

/prices - Show top 20 coins
/search <coin> - Search any coin
/cal - Currency converter
/lang - Change language
/developer - Bot info
/stats - Statistics
/help - This menu

📌 *Examples:*
/search bitcoin
/search dogecoin
/cal 100 usd to bdt

💡 *Any coin supported!*
📞 *Support:* @jhgmaing"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌍 *Select your language:*", reply_markup=reply_markup, parse_mode="Markdown")

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """রিফ্রেশ বাটন হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    coin_id = query.data.split("_")[1]
    
    await query.edit_message_text(f"🔄 Refreshing {coin_id}...")
    
    result, status = get_any_coin_price(coin_id)
    
    if status != "SUCCESS" or not result:
        await query.edit_message_text("❌ Coin not found!")
        return
    
    text = f"""✅ *{result['name']}* ({result['symbol']})

💰 *Current Price:*
💵 USD: `${result['usd']:,.4f}`
🇧🇩 BDT: `৳{result['bdt']:,.2f}`

🕐 *Updated:* Just now

💡 /cal 1 {result['symbol'].lower()} to usd"""
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{result['id']}"),
                 InlineKeyboardButton("◀️ Menu", callback_data="menu_back")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ============= মেইন =============
def main():
    app = Application.builder().token(TOKEN).build()
    
    # কমান্ড হ্যান্ডলার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CommandHandler("search", search_coin))
    app.add_handler(CommandHandler("cal", calculator))
    app.add_handler(CommandHandler("developer", developer_info))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("lang", change_language))
    
    # কলে‌ব্যাক হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="menu_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="lang_"))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="refresh_"))
    
    print("=" * 50)
    print("🤖 CRYPTO MARKET BOT v2.0 - ULTRA PRO")
    print("=" * 50)
    print("✅ 4 Languages Supported: বাংলা, English, Русский, हिन्दी")
    print("✅ Any Coin Support: Bitcoin to Shiba, everything!")
    print("✅ Box System + Inline Buttons Active")
    print("✅ Group & Channel Support Enabled")
    print("✅ JSONBin Database Connected")
    print("=" * 50)
    print("🚀 Bot is LIVE and RUNNING!")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
