import asyncio
import requests
import json
import logging
import re
import time
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== কনফিগ =====================
TOKEN = "8592158247:AAG_Bd1ZxdsPqgn5GuVRkCNP7jzJEVFXF-Q"
JSONBIN_MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
JSONBIN_BIN_ID = "69dc964236566621a8a94516"
BOT_USERNAME = "@market_bajar_bot"

JSONBIN_READ = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
JSONBIN_WRITE = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== ৮টি ভাষা (বাংলা, ইংরেজি, রুশ, হিন্দি + আরও ৪) =====================
LANG = {
    "bn": {"name":"বাংলা","flag":"🇧🇩","welcome":f"🌟 *ক্রিপ্টো মার্কেট বট ({BOT_USERNAME}) এ স্বাগতম!*\n\nযেকোনো কয়েনের লাইভ দাম USD/BDT তে দেখুন।","menu":"🌟 মেনু","prices":"💰 লাইভ দাম","search":"🔍 সার্চ","conv":"🔄 কনভার্টার","lang":"🌍 ভাষা","dev":"👨‍💻 ডেভেলপার","stats":"📊 পরিসংখ্যান","help":"❓ সাহায্য","back":"◀️ পেছনে","price_fetch":"🔄 দাম আনা হচ্ছে...","search_prompt":"🔍 কয়েনের নাম: `/search bitcoin`","not_found":"❌ পাওয়া যায়নি","error":"⚠️ এরর","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io\n📅 ভার্সন 4.0\n⚡ CoinGecko+KuCoin\n💾 JSONBin","stats_text":"📊 ইউজার: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang, /developer, /stats\n📞 {b}"},
    "en": {"name":"English","flag":"🇬🇧","welcome":f"🌟 *Welcome to Crypto Market Bot ({BOT_USERNAME})!*","menu":"🌟 Menu","prices":"💰 Live Prices","search":"🔍 Search","conv":"🔄 Converter","lang":"🌍 Language","dev":"👨‍💻 Developer","stats":"📊 Stats","help":"❓ Help","back":"◀️ Back","price_fetch":"🔄 Fetching...","search_prompt":"🔍 Enter coin: `/search bitcoin`","not_found":"❌ Not found","error":"⚠️ Error","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io\n📅 v4.0","stats_text":"📊 Users: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang, /developer, /stats\n📞 {b}"},
    "ru": {"name":"Русский","flag":"🇷🇺","welcome":f"🌟 *Добро пожаловать ({BOT_USERNAME})*","menu":"🌟 Меню","prices":"💰 Цены","search":"🔍 Поиск","conv":"🔄 Конвертер","lang":"🌍 Язык","dev":"👨‍💻 Разраб","stats":"📊 Стат","help":"❓ Помощь","back":"◀️ Назад","price_fetch":"🔄 Загрузка...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ Не найдено","error":"⚠️ Ошибка","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 Пользователей: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"},
    "hi": {"name":"हिन्दी","flag":"🇮🇳","welcome":f"🌟 *क्रिप्टो मार्केट बॉट ({BOT_USERNAME}) में स्वागत*","menu":"🌟 मेनू","prices":"💰 कीमतें","search":"🔍 खोजें","conv":"🔄 परिवर्तक","lang":"🌍 भाषा","dev":"👨‍💻 डेवलपर","stats":"📊 आँकड़े","help":"❓ सहायता","back":"◀️ पीछे","price_fetch":"🔄 लोड...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ नहीं मिला","error":"⚠️ त्रुटि","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 उपयोगकर्ता: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"},
    "es": {"name":"Español","flag":"🇪🇸","welcome":f"🌟 *Bienvenido a {BOT_USERNAME}*","menu":"🌟 Menú","prices":"💰 Precios","search":"🔍 Buscar","conv":"🔄 Convertidor","lang":"🌍 Idioma","dev":"👨‍💻 Desarrollador","stats":"📊 Estadísticas","help":"❓ Ayuda","back":"◀️ Atrás","price_fetch":"🔄 Cargando...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ No encontrado","error":"⚠️ Error","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 Usuarios: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"},
    "fr": {"name":"Français","flag":"🇫🇷","welcome":f"🌟 *Bienvenue sur {BOT_USERNAME}*","menu":"🌟 Menu","prices":"💰 Prix","search":"🔍 Rechercher","conv":"🔄 Convertisseur","lang":"🌍 Langue","dev":"👨‍💻 Développeur","stats":"📊 Statistiques","help":"❓ Aide","back":"◀️ Retour","price_fetch":"🔄 Chargement...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ Non trouvé","error":"⚠️ Erreur","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 Utilisateurs: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"},
    "de": {"name":"Deutsch","flag":"🇩🇪","welcome":f"🌟 *Willkommen bei {BOT_USERNAME}*","menu":"🌟 Menü","prices":"💰 Preise","search":"🔍 Suchen","conv":"🔄 Konverter","lang":"🌍 Sprache","dev":"👨‍💻 Entwickler","stats":"📊 Statistiken","help":"❓ Hilfe","back":"◀️ Zurück","price_fetch":"🔄 Lädt...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ Nicht gefunden","error":"⚠️ Fehler","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 Benutzer: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"},
    "zh": {"name":"中文","flag":"🇨🇳","welcome":f"🌟 *欢迎使用{BOT_USERNAME}*","menu":"🌟 菜单","prices":"💰 价格","search":"🔍 搜索","conv":"🔄 转换器","lang":"🌍 语言","dev":"👨‍💻 开发者","stats":"📊 统计","help":"❓ 帮助","back":"◀️ 返回","price_fetch":"🔄 加载中...","search_prompt":"🔍 `/search bitcoin`","not_found":"❌ 未找到","error":"⚠️ 错误","calc_usage":"📝 `/cal 100 usd to bdt`","calc_result":"✅ {amount} {f} = {res:.8f} {t}","dev_info":"👨‍💻 @bot_developer_io","stats_text":"📊 用户: {u}\n🕐 {t}","help_text":"❓ /prices, /search, /cal, /lang\n📞 {b}"}
}
SUPPORTED_LANGS = list(LANG.keys())

# ===================== ডাটাবেস ফাংশন (বিস্তারিত) =====================
def get_db():
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY}
        r = requests.get(JSONBIN_READ, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("record", {"users": {}, "total_commands": 0})
    except: pass
    return {"users": {}, "total_commands": 0}

def save_db(data):
    try:
        headers = {"X-Master-Key": JSONBIN_MASTER_KEY, "Content-Type": "application/json"}
        requests.put(JSONBIN_WRITE, json=data, headers=headers, timeout=5)
    except: pass

def get_user_lang(user_id):
    db = get_db()
    return db.get("users", {}).get(str(user_id), {}).get("lang", "bn")

def set_user_lang(user_id, lang):
    db = get_db()
    if "users" not in db: db["users"] = {}
    if str(user_id) not in db["users"]: db["users"][str(user_id)] = {}
    db["users"][str(user_id)]["lang"] = lang
    save_db(db)

def update_stats(user_id, command):
    db = get_db()
    if "users" not in db: db["users"] = {}
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"joined": str(datetime.now()), "commands": 0}
    db["users"][str(user_id)]["commands"] = db["users"][str(user_id)].get("commands", 0) + 1
    db["total_commands"] = db.get("total_commands", 0) + 1
    save_db(db)

# ===================== ক্রিপ্টো API (৩টি ব্যাকআপ + ক্যাশ) =====================
price_cache = {"data": None, "time": 0, "source": None}

def fetch_coingecko():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=25&page=1&sparkline=false"
        r = requests.get(url, timeout=8)
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
    except: pass
    return None, None

def fetch_kucoin():
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("ticker", [])
            result = []
            for t in data[:25]:
                if t.get("symbol", "").endswith("-USDT"):
                    price = float(t.get("last", 0))
                    if price > 0:
                        sym = t["symbol"].replace("-USDT", "")
                        result.append({
                            "name": sym,
                            "symbol": sym,
                            "usd": price,
                            "bdt": price * 118,
                            "change": float(t.get("changeRate", 0)) * 100
                        })
            if result:
                return result, "KuCoin"
    except: pass
    return None, None

def fetch_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            result = []
            for t in data:
                if t.get("symbol", "").endswith("USDT"):
                    price = float(t.get("lastPrice", 0))
                    if price > 0:
                        sym = t["symbol"].replace("USDT", "")
                        result.append({
                            "name": sym,
                            "symbol": sym,
                            "usd": price,
                            "bdt": price * 118,
                            "change": float(t.get("priceChangePercent", 0))
                        })
            if result:
                return result[:25], "Binance"
    except: pass
    return None, None

def get_top_coins():
    global price_cache
    now = time.time()
    if price_cache["data"] and now - price_cache["time"] < 60:
        return price_cache["data"]
    for fetcher in [fetch_coingecko, fetch_kucoin, fetch_binance]:
        data, source = fetcher()
        if data:
            price_cache = {"data": data, "time": now, "source": source}
            return data
    # ফাইনাল ব্যাকআপ
    fallback = [
        {"name":"Bitcoin","symbol":"BTC","usd":70000,"bdt":8260000,"change":2.5},
        {"name":"Ethereum","symbol":"ETH","usd":3500,"bdt":413000,"change":1.8},
        {"name":"BNB","symbol":"BNB","usd":600,"bdt":70800,"change":-0.5},
        {"name":"Solana","symbol":"SOL","usd":150,"bdt":17700,"change":5.2},
        {"name":"XRP","symbol":"XRP","usd":0.6,"bdt":70.8,"change":-1.2},
        {"name":"Dogecoin","symbol":"DOGE","usd":0.15,"bdt":17.7,"change":3.0},
        {"name":"Cardano","symbol":"ADA","usd":0.45,"bdt":53.1,"change":-0.8},
        {"name":"Polygon","symbol":"MATIC","usd":0.8,"bdt":94.4,"change":1.5}
    ]
    price_cache = {"data": fallback, "time": now, "source": "Fallback"}
    return fallback

def search_coin_multi(query):
    """একাধিক API ব্যবহার করে সার্চ – প্রথমে CoinGecko exact, তারপর Kucoin/Binance"""
    # 1. CoinGecko search + price
    try:
        s_url = f"https://api.coingecko.com/api/v3/search?query={query}"
        s_resp = requests.get(s_url, timeout=8)
        if s_resp.status_code == 200:
            s_data = s_resp.json()
            coins = s_data.get("coins", [])
            if coins:
                best = None
                ql = query.lower()
                for c in coins:
                    if c["symbol"].lower() == ql or c["name"].lower() == ql:
                        best = c
                        break
                if not best:
                    best = coins[0]
                coin_id = best["id"]
                name = best["name"]
                symbol = best["symbol"].upper()
                p_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,bdt"
                p_resp = requests.get(p_url, timeout=8)
                if p_resp.status_code == 200:
                    p_data = p_resp.json()
                    if coin_id in p_data:
                        usd = p_data[coin_id].get("usd", 0)
                        bdt = p_data[coin_id].get("bdt", usd*118)
                        return {"name": name, "symbol": symbol, "usd": usd, "bdt": bdt, "id": coin_id}
    except: pass
    # 2. KuCoin থেকে খোঁজ
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            tickers = r.json().get("data", {}).get("ticker", [])
            for t in tickers:
                if query.upper() in t.get("symbol", "") and t["symbol"].endswith("-USDT"):
                    price = float(t.get("last", 0))
                    sym = t["symbol"].replace("-USDT", "")
                    return {"name": sym, "symbol": sym, "usd": price, "bdt": price*118, "id": sym.lower()}
    except: pass
    # 3. Binance
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            for t in data:
                if t.get("symbol", "").endswith("USDT") and query.upper() in t["symbol"]:
                    price = float(t.get("lastPrice", 0))
                    sym = t["symbol"].replace("USDT", "")
                    return {"name": sym, "symbol": sym, "usd": price, "bdt": price*118, "id": sym.lower()}
    except: pass
    return None

def get_crypto_rate(currency):
    curr = currency.lower()
    if curr in ["usd", "usdt"]: return 1
    if curr == "bdt": return 118
    top = get_top_coins()
    for c in top:
        if c["symbol"].lower() == curr:
            return c["usd"]
    static = {"btc":70000, "eth":3500, "bnb":600, "sol":150, "xrp":0.6, "doge":0.15, "wbtc":70000, "ada":0.45, "matic":0.8, "dot":7, "ltc":80}
    return static.get(curr, 1)

# ===================== বক্স সিস্টেম (ইনলাইন কিবোর্ড) =====================
def get_main_keyboard(lang_code):
    t = LANG[lang_code]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["prices"], callback_data="menu_prices"),
         InlineKeyboardButton(t["search"], callback_data="menu_search")],
        [InlineKeyboardButton(t["conv"], callback_data="menu_conv"),
         InlineKeyboardButton(t["lang"], callback_data="menu_lang")],
        [InlineKeyboardButton(t["dev"], callback_data="menu_dev"),
         InlineKeyboardButton(t["stats"], callback_data="menu_stats")],
        [InlineKeyboardButton(t["help"], callback_data="menu_help")]
    ])

# ===================== টেলিগ্রাম হ্যান্ডলার (সব কমান্ড) =====================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/start")
    lang = get_user_lang(uid)
    await update.message.reply_text(LANG[lang]["welcome"], reply_markup=get_main_keyboard(lang), parse_mode="Markdown")

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_user_lang(uid)
    action = q.data.split("_")[1]

    if action == "prices":
        await q.edit_message_text(LANG[lang]["price_fetch"])
        coins = get_top_coins()
        msg = f"💰 *{LANG[lang]['prices']}*\n\n"
        for c in coins[:20]:
            emoji = "📈" if c["change"] >= 0 else "📉"
            msg += f"{emoji} *{c['name']}* ({c['symbol']})\n   💵 ${c['usd']:,.2f} | ৳{c['bdt']:,.2f}   {c['change']:+.2f}%\n\n"
        msg += f"\n🔍 /search <coin>"
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "search":
        msg = LANG[lang]["search_prompt"]
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "conv":
        msg = LANG[lang]["calc_usage"]
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "lang":
        kb = []
        row = []
        for i, lc in enumerate(SUPPORTED_LANGS):
            row.append(InlineKeyboardButton(f"{LANG[lc]['flag']} {LANG[lc]['name']}", callback_data=f"lang_{lc}"))
            if (i+1) % 2 == 0 or i == len(SUPPORTED_LANGS)-1:
                kb.append(row)
                row = []
        kb.append([InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")])
        await q.edit_message_text("🌍 ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif action == "dev":
        msg = LANG[lang]["dev_info"]
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "stats":
        db = get_db()
        total_users = len(db.get("users", {}))
        total_cmds = db.get("total_commands", 0)
        msg = LANG[lang]["stats_text"].format(u=total_users, t=datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + f"\n📊 মোট কমান্ড: {total_cmds}"
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "help":
        msg = LANG[lang]["help_text"].format(b=BOT_USERNAME)
        back = InlineKeyboardMarkup([[InlineKeyboardButton(LANG[lang]["back"], callback_data="menu_back")]])
        await q.edit_message_text(msg, reply_markup=back, parse_mode="Markdown")

    elif action == "back":
        await q.edit_message_text(LANG[lang]["welcome"], reply_markup=get_main_keyboard(lang), parse_mode="Markdown")

async def language_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    new_lang = q.data.split("_")[1]
    set_user_lang(uid, new_lang)
    await q.edit_message_text(LANG[new_lang]["welcome"], reply_markup=get_main_keyboard(new_lang), parse_mode="Markdown")

# কমান্ড হ্যান্ডলার
async def prices_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/prices")
    lang = get_user_lang(uid)
    await update.message.reply_text(LANG[lang]["price_fetch"])
    coins = get_top_coins()
    msg = f"💰 *{LANG[lang]['prices']}*\n\n"
    for c in coins[:20]:
        emoji = "📈" if c["change"] >= 0 else "📉"
        msg += f"{emoji} *{c['name']}* ({c['symbol']})\n   💵 ${c['usd']:,.2f} | ৳{c['bdt']:,.2f}   {c['change']:+.2f}%\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def search_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/search")
    lang = get_user_lang(uid)
    if not ctx.args:
        await update.message.reply_text(LANG[lang]["search_prompt"], parse_mode="Markdown")
        return
    query = " ".join(ctx.args)
    await update.message.reply_text(f"🔄 Searching *{query}*...", parse_mode="Markdown")
    coin = search_coin_multi(query)
    if not coin or coin["usd"] == 0:
        await update.message.reply_text(LANG[lang]["not_found"], parse_mode="Markdown")
        return
    msg = f"✅ *{coin['name']}* ({coin['symbol']})\n\n💰 *Current Price*\n💵 ${coin['usd']:,.4f} USD\n🇧🇩 ৳{coin['bdt']:,.2f} BDT\n\n💡 /cal 1 {coin['symbol'].lower()} to usd"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def calc_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/cal")
    lang = get_user_lang(uid)
    if not ctx.args:
        await update.message.reply_text(LANG[lang]["calc_usage"], parse_mode="Markdown")
        return
    try:
        txt = " ".join(ctx.args).lower()
        m = re.match(r"(\d+(?:\.\d+)?)\s+(\w+)\s+to\s+(\w+)", txt)
        if not m:
            await update.message.reply_text(LANG[lang]["calc_usage"], parse_mode="Markdown")
            return
        amount = float(m.group(1))
        frm = m.group(2)
        to = m.group(3)
        rate_f = get_crypto_rate(frm)
        rate_t = get_crypto_rate(to)
        usd_val = amount * rate_f
        result = usd_val / rate_t
        msg = LANG[lang]["calc_result"].format(amount=amount, f=frm.upper(), res=result, t=to.upper())
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Calc error: {e}")
        await update.message.reply_text(LANG[lang]["error"], parse_mode="Markdown")

async def dev_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/developer")
    lang = get_user_lang(uid)
    await update.message.reply_text(LANG[lang]["dev_info"], parse_mode="Markdown")

async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/stats")
    lang = get_user_lang(uid)
    db = get_db()
    total_users = len(db.get("users", {}))
    total_cmds = db.get("total_commands", 0)
    msg = LANG[lang]["stats_text"].format(u=total_users, t=datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + f"\n📊 মোট কমান্ড: {total_cmds}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/help")
    lang = get_user_lang(uid)
    await update.message.reply_text(LANG[lang]["help_text"].format(b=BOT_USERNAME), parse_mode="Markdown")

async def lang_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_stats(uid, "/lang")
    lang = get_user_lang(uid)
    kb = []
    row = []
    for i, lc in enumerate(SUPPORTED_LANGS):
        row.append(InlineKeyboardButton(f"{LANG[lc]['flag']} {LANG[lc]['name']}", callback_data=f"lang_{lc}"))
        if (i+1) % 2 == 0 or i == len(SUPPORTED_LANGS)-1:
            kb.append(row)
            row = []
    await update.message.reply_text("🌍 ভাষা নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(kb))

# অতিরিক্ত মজার কমান্ড (বিকল্প)
async def about_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 *{BOT_USERNAME}*\n\nবিশ্বের যেকোনো ক্রিপ্টো কয়েনের লাইভ দাম ও কনভার্টার।\nডেভেলপার: @bot_developer_io", parse_mode="Markdown")

async def donate_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🙏 *দান করতে চাইলে*\nBTC: bc1q...\nETH: 0x...\nআপনার সাহায্য বটকে বাঁচিয়ে রাখবে।", parse_mode="Markdown")

async def ping_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    await update.message.reply_text("🏓 পং!")
    end = time.time()
    await update.message.reply_text(f"⏱️ লেটেন্সি: {(end-start)*1000:.2f} ms")

# ===================== মেইন =====================
def main():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prices", prices_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("cal", calc_command))
    app.add_handler(CommandHandler("developer", dev_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("donate", donate_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="menu_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="lang_"))

    print("✅ বট চালু হয়েছে – বিশাল মারাত্মক ভার্সন 4.0")
    print(f"📊 {len(SUPPORTED_LANGS)}টি ভাষা সাপোর্টেড")
    print("🚀 Render ফ্রি টায়ারে অপটিমাইজড")
    app.run_polling()

if __name__ == "__main__":
    main()
