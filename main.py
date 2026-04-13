import requests
import json
import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

# ============= কনফিগারেশন =============
# আপনার JSONBin তথ্য直接用
TOKEN = os.environ.get("TOKEN", "YOUR_BOT_TOKEN_HERE")
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_BIN_ID = "69dc964236566621a8a94516"

# JSONBin API URLs
JSONBIN_READ_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
JSONBIN_WRITE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ভাষা সমূহ
LANGUAGES = {
    "bn": {
        "name": "বাংলা",
        "flag": "🇧🇩",
        "welcome": "🚀 *ক্রিপ্টো মার্কেট বটে স্বাগতম!*\n\nআমি লাইভ ক্রিপ্টো প্রাইস USD ও BDT তে দেখাতে পারি।",
        "price_fetching": "🔄 লাইভ দাম সংগ্রহ করা হচ্ছে...",
        "api_error": "❌ এপিআই এরর! পরে আবার চেষ্টা করুন।",
        "help_text": """🤖 *ক্রিপ্টো মার্কেট বট - হেল্প মেনু*

📌 *বেসিক কমান্ড:*
/prices - লাইভ ক্রিপ্টো দাম দেখুন
/list - সব কয়েনের তালিকা দেখুন
/cal - কারেন্সি কনভার্টার
/lang - ভাষা পরিবর্তন করুন

📌 *কনভার্টার উদাহরণ:*
/cal 100 usd to bdt
/cal 50 bdt to usd
/cal 0.5 btc to usd

📌 *অন্যান্য কমান্ড:*
/developer - বট ডেভেলপার তথ্য
/help - এই মেনু দেখুন
/stats - বট পরিসংখ্যান

💡 *সাপোর্টেড কারেন্সি:* USD, BDT, BTC, ETH, USDT""",
        "prices_title": "💰 *লাইভ ক্রিপ্টো দাম*\n\n",
        "list_title": "📋 *উপলব্ধ কয়েন সমূহ*\n\n",
        "developer_text": "👨‍💻 *ডেভেলপার তথ্য*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 ভার্সন: 2.0\n⚡ পাওয়ার্ড বাই: CoinGecko API\n💾 ডাটাবেস: JSONBin",
        "no_data": "❌ কোনো ডাটা পাওয়া যায়নি!",
        "calc_usage": "ব্যবহার: /cal 100 usd to bdt\nউদাহরণ: /cal 50 bdt to usd",
        "calc_error": "❌ অনিয়মিত ফরম্যাট!",
        "calc_result": "✅ {amount} {from_curr} = {result:.6f} {to_curr}"
    },
    "en": {
        "name": "English",
        "flag": "🇬🇧",
        "welcome": "🚀 *Welcome to Crypto Market Bot!*\n\nI can show you live crypto prices in USD & BDT.",
        "price_fetching": "🔄 Fetching live prices...",
        "api_error": "❌ API Error! Please try again later.",
        "help_text": """🤖 *Crypto Market Bot - Help Menu*

📌 *Basic Commands:*
/prices - Show live crypto prices
/list - Show all available coins
/cal - Currency converter
/lang - Change language

📌 *Converter Examples:*
/cal 100 usd to bdt
/cal 50 bdt to usd
/cal 0.5 btc to usd

📌 *Other Commands:*
/developer - Bot developer info
/help - Show this menu
/stats - Bot statistics

💡 *Supported currencies:* USD, BDT, BTC, ETH, USDT""",
        "prices_title": "💰 *Live Crypto Prices*\n\n",
        "list_title": "📋 *Available Coins*\n\n",
        "developer_text": "👨‍💻 *Developer Info*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 Version: 2.0\n⚡ Powered by: CoinGecko API\n💾 Database: JSONBin",
        "no_data": "❌ No data found!",
        "calc_usage": "Usage: /cal 100 usd to bdt\nExample: /cal 50 bdt to usd",
        "calc_error": "❌ Invalid format!",
        "calc_result": "✅ {amount} {from_curr} = {result:.6f} {to_curr}"
    },
    "ru": {
        "name": "Русский",
        "flag": "🇷🇺",
        "welcome": "🚀 *Добро пожаловать в Crypto Market Bot!*\n\nЯ показываю живые цены криптовалют в USD и BDT.",
        "price_fetching": "🔄 Получение живых цен...",
        "api_error": "❌ Ошибка API! Пожалуйста, попробуйте позже.",
        "help_text": """🤖 *Crypto Market Bot - Помощь*

📌 *Основные команды:*
/prices - Показать живые цены
/list - Список всех монет
/cal - Конвертер валют
/lang - Сменить язык

📌 *Примеры конвертера:*
/cal 100 usd to bdt
/cal 50 bdt to usd
/cal 0.5 btc to usd

📌 *Другие команды:*
/developer - Информация о разработчике
/help - Показать это меню
/stats - Статистика бота

💡 *Поддерживаемые валюты:* USD, BDT, BTC, ETH, USDT""",
        "prices_title": "💰 *Живые цены криптовалют*\n\n",
        "list_title": "📋 *Доступные монеты*\n\n",
        "developer_text": "👨‍💻 *Информация о разработчике*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 Версия: 2.0\n⚡ Работает на: CoinGecko API\n💾 База данных: JSONBin",
        "no_data": "❌ Данные не найдены!",
        "calc_usage": "Использование: /cal 100 usd to bdt\nПример: /cal 50 bdt to usd",
        "calc_error": "❌ Неверный формат!",
        "calc_result": "✅ {amount} {from_curr} = {result:.6f} {to_curr}"
    },
    "hi": {
        "name": "हिन्दी",
        "flag": "🇮🇳",
        "welcome": "🚀 *क्रिप्टो मार्केट बॉट में आपका स्वागत है!*\n\nमैं USD और BDT में लाइव क्रिप्टो कीमतें दिखा सकता हूँ।",
        "price_fetching": "🔄 लाइव कीमतें लाई जा रही हैं...",
        "api_error": "❌ API त्रुटि! कृपया बाद में पुनः प्रयास करें।",
        "help_text": """🤖 *क्रिप्टो मार्केट बॉट - सहायता मेनू*

📌 *बेसिक कमांड:*
/prices - लाइव क्रिप्टो कीमतें देखें
/list - सभी उपलब्ध सिक्के देखें
/cal - मुद्रा कनवर्टर
/lang - भाषा बदलें

📌 *कनवर्टर उदाहरण:*
/cal 100 usd to bdt
/cal 50 bdt to usd
/cal 0.5 btc to usd

📌 *अन्य कमांड:*
/developer - बॉट डेवलपर जानकारी
/help - यह मेनू देखें
/stats - बॉट आँकड़े

💡 *समर्थित मुद्राएँ:* USD, BDT, BTC, ETH, USDT""",
        "prices_title": "💰 *लाइव क्रिप्टो कीमतें*\n\n",
        "list_title": "📋 *उपलब्ध सिक्के*\n\n",
        "developer_text": "👨‍💻 *डेवलपर जानकारी*\n\n• @jhgmaing\n• @bot_developer_io\n\n📅 संस्करण: 2.0\n⚡ संचालित: CoinGecko API\n💾 डेटाबेस: JSONBin",
        "no_data": "❌ कोई डेटा नहीं मिला!",
        "calc_usage": "उपयोग: /cal 100 usd to bdt\nउदाहरण: /cal 50 bdt to usd",
        "calc_error": "❌ अमान्य प्रारूप!",
        "calc_result": "✅ {amount} {from_curr} = {result:.6f} {to_curr}"
    }
}

# ============= ডাটাবেস ফাংশন =============
def get_user_data():
    """ইউজার ডাটা রিড করা"""
    headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
    try:
        response = requests.get(JSONBIN_READ_URL, headers=headers)
        if response.status_code == 200:
            return response.json().get("record", {"users": {}})
        else:
            logger.error(f"Read error: {response.status_code}")
            return {"users": {}}
    except Exception as e:
        logger.error(f"Get user data error: {e}")
        return {"users": {}}

def save_user_data(data):
    """ইউজার ডাটা সেভ করা"""
    headers = {
        "X-Master-Key": JSONBIN_MASTER_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(JSONBIN_WRITE_URL, json=data, headers=headers)
        if response.status_code == 200:
            logger.info("✅ Data saved to JSONBin")
            return True
        else:
            logger.error(f"Save error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Save user data error: {e}")
        return False

def get_user_lang(user_id):
    """ইউজারের ভাষা পাওয়া"""
    data = get_user_data()
    return data["users"].get(str(user_id), {}).get("language", "bn")

def set_user_lang(user_id, lang):
    """ইউজারের ভাষা সেট করা"""
    data = get_user_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {}
    data["users"][str(user_id)]["language"] = lang
    save_user_data(data)

# ============= ক্রিপ্টো এপিআই ফাংশন =============
def get_crypto_prices():
    """CoinGecko থেকে লাইভ প্রাইস আনা"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,ripple,dogecoin,solana,cardano,polkadot,matic-network,litecoin&vs_currencies=usd,bdt"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        coin_names = {
            "bitcoin": "₿ Bitcoin (BTC)",
            "ethereum": "Ξ Ethereum (ETH)",
            "binancecoin": "🟡 Binance Coin (BNB)",
            "ripple": "💧 XRP (XRP)",
            "dogecoin": "🐕 Dogecoin (DOGE)",
            "solana": "◎ Solana (SOL)",
            "cardano": "📊 Cardano (ADA)",
            "polkadot": "🔗 Polkadot (DOT)",
            "matic-network": "🟣 Polygon (MATIC)",
            "litecoin": "⚡ Litecoin (LTC)"
        }
        
        result = []
        for coin_id, name in coin_names.items():
            if coin_id in data:
                usd_price = data[coin_id]["usd"]
                bdt_price = data[coin_id].get("bdt", usd_price * 118)
                result.append({
                    "name": name,
                    "usd": usd_price,
                    "bdt": bdt_price
                })
        return result
    except Exception as e:
        logger.error(f"Crypto API Error: {e}")
        return None

# ============= টেলিগ্রাম কমান্ড হ্যান্ডলার =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌍 *Select your language / আপনার ভাষা নির্বাচন করুন:*\n\n"
        "🇧🇩 বাংলा\n🇬🇧 English\n🇷🇺 Русский\n🇮🇳 हिन्दी",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    
    set_user_lang(user_id, lang)
    
    text = LANGUAGES[lang]["welcome"]
    await query.edit_message_text(text, parse_mode="Markdown")
    
    # হেল্প মেনু দেখান
    await help_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = LANGUAGES[lang]["help_text"]
    await update.message.reply_text(text, parse_mode="Markdown")

async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    await update.message.reply_text(LANGUAGES[lang]["price_fetching"])
    
    prices_data = get_crypto_prices()
    if not prices_data:
        await update.message.reply_text(LANGUAGES[lang]["api_error"])
        return
    
    text = LANGUAGES[lang]["prices_title"]
    for coin in prices_data[:10]:
        text += f"• {coin['name']}: ${coin['usd']:,.2f} | ৳{coin['bdt']:,.2f}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def list_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    coins = """• Bitcoin (BTC)
• Ethereum (ETH)
• Binance Coin (BNB)
• XRP (XRP)
• Dogecoin (DOGE)
• Solana (SOL)
• Cardano (ADA)
• Polkadot (DOT)
• Polygon (MATIC)
• Litecoin (LTC)"""
    
    text = LANGUAGES[lang]["list_title"] + coins
    await update.message.reply_text(text, parse_mode="Markdown")

async def calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not context.args:
        await update.message.reply_text(LANGUAGES[lang]["calc_usage"])
        return
    
    try:
        text = " ".join(context.args).lower()
        match = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s+to\s+(\w+)", text)
        if not match:
            await update.message.reply_text(LANGUAGES[lang]["calc_error"])
            return
        
        amount = float(match.group(1))
        from_curr = match.group(2)
        to_curr = match.group(3)
        
        # বেসিক রেট
        rates = {
            "usd": 1,
            "bdt": 118,  # 1 USD = 118 BDT
            "btc": 65000,  # Approx
            "eth": 3500,   # Approx
            "usdt": 1
        }
        
        if from_curr not in rates or to_curr not in rates:
            await update.message.reply_text("❌ Unsupported currency! Use: usd, bdt, btc, eth, usdt")
            return
        
        usd_value = amount * rates[from_curr]
        result = usd_value / rates[to_curr]
        
        result_text = LANGUAGES[lang]["calc_result"].format(
            amount=amount,
            from_curr=from_curr.upper(),
            result=result,
            to_curr=to_curr.upper()
        )
        await update.message.reply_text(result_text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = LANGUAGES[lang]["developer_text"]
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    data = get_user_data()
    total_users = len(data.get("users", {}))
    
    text = f"""📊 *Bot Statistics*

👥 Total Users: {total_users}
🌍 Languages: Bengali, English, Russian, Hindi
⚡ Status: Active
📅 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💾 Database: JSONBin
🔗 API: CoinGecko"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌍 Select your language:", reply_markup=reply_markup)

# ============= মেইন ফাংশন =============
def main():
    app = Application.builder().token(TOKEN).build()
    
    # হ্যান্ডলার রেজিস্টার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices))
    app.add_handler(CommandHandler("list", list_coins))
    app.add_handler(CommandHandler("cal", calculator))
    app.add_handler(CommandHandler("developer", developer_info))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("lang", change_language))
    app.add_handler(CallbackQueryHandler(language_handler, pattern="lang_"))
    
    print("🤖 Bot is running with 4 languages support...")
    print("✅ JSONBin Connected!")
    app.run_polling()

if __name__ == "__main__":
    main()
