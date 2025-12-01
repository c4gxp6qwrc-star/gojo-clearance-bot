#!/usr/bin/env python3
"""
Improved GOJO Home Depot Clearance Helper Bot

- Parses ADMIN_IDS as integers (comma separated).
- Adds image preprocessing to improve barcode decoding success.
- Returns all decoded barcodes if multiple are found.
- Adds logging and better error handling for file download / image open.
- Keeps original UX, commands and bilingual support.
"""

import os
import logging
from io import BytesIO
from typing import Optional, Set, List

from PIL import Image, ImageOps
from pyzbar.pyzbar import decode as decode_barcodes

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gojo_bot")

# Bot token from environment (Render env var BOT_TOKEN)
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin IDs (comma-separated Telegram user IDs in ADMIN_IDS env var)
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "").strip()

def parse_admin_ids(env: str) -> Set[int]:
    ids = set()
    if not env:
        return ids
    for piece in env.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            ids.add(int(piece))
        except ValueError:
            logger.warning("Skipping invalid ADMIN_IDS entry: %r", piece)
    return ids

ADMIN_IDS: Set[int] = parse_admin_ids(ADMIN_IDS_ENV)

def is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    return user.id in ADMIN_IDS

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    # 'en', 'am', or 'bi' (both). Default: 'bi'
    return context.user_data.get("lang", "bi")

def format_text(en: str, am: str, lang: str) -> str:
    """Return English, Amharic, or both based on lang flag."""
    en = en.strip()
    am = am.strip()
    if lang == "en":
        return en
    if lang == "am":
        return am
    # bilingual
    return f"{en}\n\n{am}"

def build_links_from_code(code: str, store: Optional[str], lang: str) -> str:
    code = code.strip()

    home_depot_search = f"https://www.homedepot.com/s/{code}"
    google_search = f"https://www.google.com/search?q={code}+Home+Depot+clearance"

    store_line_en = ""
    store_line_am = ""
    if store:
        store_line_en = f"🏬 Preferred store: #{store}"
        store_line_am = f"🏬 የተመረጠው መደብር ቁጥር፡ #{store}"

    en = (
        f"🔢 *Code detected:* `{{code}}`\n\n"
        f"🧡 *Home Depot search:*\n{{home_depot_search}}\n\n"
        f"🌐 *Google search:*\n{{google_search}}\n\n"
        f"{{store_line_en}}\n\n"
        "👉 Use your Home Depot app or in‑store scanner to check final clearance price."
    )

    am = (
        f"🔢 *የተነበበው ባርኮድ ኮድ:* `{{code}}`\n\n"
        f"🧡 *በ Home Depot ፍለጋ:*\n{{home_depot_search}}\n\n"
        f"🌐 *በ Google ፍለጋ:*\n{{google_search}}\n\n"
        f"{{store_line_am}}\n\n"
        "👉 የመጨረሻ ዋጋን ለመወቅ በ Home Depot መተግበሪያ ወይም በውስጥ ስካነር ይፈትሹ።"
    )

    return format_text(en, am, lang)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    store = context.user_data.get("store")

    store_line_en = f"\n\n🏬 Current preferred store: #{store}" if store else ""
    store_line_am = f"\n\n🏬 አሁን የተመረጠው መደብር፡ #{store}" if store else ""

    en = (
        "👋 Welcome to *GOJO Home Depot Clearance Helper Bot*!\n\n"
        "I help you quickly check item barcodes while you hunt for clearance deals.\n\n"
        "📸 Send me a *photo of a barcode* or\n"
        "⌨️ *Type the barcode number* (UPC/EAN)."
        f"{{store_line_en}}\n\n"
        "🗣 Language: English + Amharic (use /lang to change).\n"
        "🏬 Use /store to set your favorite Home Depot store number."
    )

    am = (
        "👋 ወደ *GOJO Home Depot Clearance አጋዥ ቦት* እንኳን ደህና መጡ!\n\n"
        "በክሊራንስ ሽያጭ ጊዜ የእቃ ባርኮድ ፈጣን ምርመራ እርዳታ እሰጣችሁ።\n\n"
        "📸 *የባርኮድ ፎቶ* ይላኩ ወይም\n"
        "⌨️ *የባርኮዱን ቁጥር* ብቻ ይጻፉ (UPC/EAN)."
        f"{{store_line_am}}\n\n"
        "🗣 ቋንቋ፡ እንግሊዝኛ + አማርኛ (ለመቀየር /lang ይጠቀሙ).\n"
        "🏬 የሚወዱትን Home Depot መደብር ቁጥር ለመያዝ /store ይጠቀሙ።"
    )

    text = format_text(en, am, lang)
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    en = (
        "📌 *How to use GOJO Clearance Bot*\n\n"
        "1️⃣ Take a clear photo of the product barcode.\n"
        "2️⃣ Send the photo here, or type the barcode digits.\n"
        "3️⃣ I’ll send you quick links to search that code on Home Depot and Google.\n\n"
        "Commands:\n"
        "/start – Welcome message\n"
        "/help – This help menu\n"
        "/store 1234 – Set your preferred store number\n"
        "/lang en|am|bi – Change language (English, Amharic, or both)"
    )
    am = (
        "📌 *GOJO Clearance Bot እንዴት እንደሚጠቀሙበት*\n\n"
        "1️⃣ የእቃውን ባርኮድ ግልጽ ፎቶ ይውሰዱ።\n"
        "2️⃣ ፎቶውን ወደዚዅ ይላኩ ወይም የባርኮዱን ቁጥር ብቻ ይጻፉ።\n"
        "3️⃣ በ Home Depot እና Google ላይ በፍጥነት ለመፈለግ አገናኞችን እልክላችኋለሁ።\n\n"
        "ትእዛዞች፦\n"
        "/start – መግቢያ መልዕክት\n"
        "/help – የእርዳታ መመሪያ\n"
        "/store 1234 – የሚወዱትን መደብር ቁጥር ለመመዝገብ\n"
        "/lang en|am|bi – ቋንቋን ለመቀየር (እንግሊዝኛ፣ አማርኛ ወይም በአንድላይ)"
    )
    await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        choice = context.args[0].lower()
    else:
        choice = ""

    if choice not in {"en", "am", "bi"}:
        # Show current setting and options
        current = get_lang(context)
        en = (
            f"🌐 Current language mode: *{{current.upper()}}*\n\n"
            "Use one of these:\n"
            "`/lang en` – English only\n"
            "`/lang am` – Amharic only\n"
            "`/lang bi` – Both English & Amharic"
        )
        am = (
            f"🌐 አሁን የተመረጠው ቋንቋ: *{{current.upper()}}*\n\n"
            "ከእነዚህ መካከል ይምረጡ፦\n"
            "`/lang en` – እንግሊዝኛ ብቻ\n"
            "`/lang am` – አማርኛ ብቻ\n"
            "`/lang bi` – ሁለቱም በአንድ ጊዜ"
        )
        text = format_text(en, am, get_lang(context))
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    context.user_data["lang"] = choice

    if choice == "en":
        text = "✅ Language set to *English only*."
        am_text = "✅ ቋንቋ ወደ *እንግሊዝኛ ብቻ* ተቀይሯል።"
    elif choice == "am":
        text = "✅ Language set to *Amharic only*."
        am_text = "✅ ቋንቋ ወደ *አማርኛ ብቻ* ተቀይሯል።"
    else:
        text = "✅ Language set to *both English & Amharic*."
        am_text = "✅ ቋንቋ ወደ *እንግሊዝኛ እና አማርኛ* ተቀይሯል።"

    await update.message.reply_text(format_text(text, am_text, "bi"), parse_mode="Markdown")

async def store_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)

    if not context.args:
        current = context.user_data.get("store")
        if current:
            en = f"🏬 Your current preferred store is: *#{current}*\nUse `/store 1234` to change it."
            am = f"🏬 አሁን የተመረጠው መደብር፡ *#{current}*\nለመቀየር `/store 1234` ይጻፉ።"
        else:
            en = "🏬 You haven’t set a preferred store yet. Use `/store 1234` to set one."
            am = "🏬 እስካሁን የተመረጠ መደብር አልተያዘም። ለመመዝገብ `/store 1234` ይጻፉ።"
        await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    store = context.args[0].strip()
    if not store.isdigit():
        en = "❗ Please send only the store number. Example: `/store 1553`"
        am = "❗ የመደብሩን ቁጥር ብቻ ያስገቡ። ምሳሌ፦ `/store 1553`"
        await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    context.user_data["store"] = store
    en = f"✅ Preferred store set to *#{store}*."
    am = f"✅ የተመረጠው መደብር *#{store}* ተሆኗል።"
    await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    lang = get_lang(context)

    # Ignore commands here
    if text.startswith("/"):
        return

    if text.isdigit() and 8 <= len(text) <= 16:
        # Count scan
        bot_data = context.bot_data
        bot_data["total_scans"] = bot_data.get("total_scans", 0) + 1

        store = context.user_data.get("store")
        reply_text = build_links_from_code(text, store, lang)
        await update.message.reply_text(reply_text, parse_mode="Markdown")
    else:
        en = "Please send a *barcode number* (just digits) or a *photo of a barcode* 😊"
        am = "እባክዎን *የባርኮድ ቁጥር* ብቻ ወይም *የባርኮድ ፎቶ* ይላኩ 😊"
        await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")


def _preprocess_for_decode(image: Image.Image) -> Image.Image:
    """
    Preprocess the PIL Image to improve barcode detection:
    - Convert to L (grayscale)
    - Autocontrast
    - Upscale small images modestly (helps when users send tiny thumbnails)
    """
    try:
        img = image.convert("L")
    except Exception:
        img = image.copy().convert("L")

    # Autocontrast to boost readability
    img = ImageOps.autocontrast(img)

    # Upscale small images (but keep reasonable size)
    max_small_dim = 800
    w, h = img.size
    if max(w, h) < max_small_dim:
        scale = max_small_dim / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    return img

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    lang = get_lang(context)

    if not msg or not msg.photo:
        en = "I didn’t find a photo 🤔 – please send a clear picture of the barcode."
        am = "ፎቶ አልተገኘም 🤔 – ግልጽ የባርኮድ ፎቶ ይላኩ።"
        await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    photo = msg.photo[-1]

    # Download to memory with exception handling
    buf = BytesIO()
    try:
        file = await photo.get_file()
        await file.download_to_memory(out=buf)
        buf.seek(0)
    except Exception as e:
        logger.exception("Failed to download photo: %s", e)
        en = "Could not download the photo. Please try again."
        am = "ፎቶውን ማውረድ አልቻልንም። እባክዎን እንደገና ይሞክሩ።"
        await msg.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    try:
        image = Image.open(buf)
    except Exception as e:
        logger.exception("Failed to open image from buffer: %s", e)
        en = f"Could not open the image. Error: {{e}}"
        am = "ፎቶውን መክፈት አልተቻለም። እባክዎን እንደገና ይሞክሩ።"
        await msg.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    # Preprocess to improve decode chances
    processed = _preprocess_for_decode(image)

    try:
        decoded_objects = decode_barcodes(processed)
    except Exception as e:
        logger.exception("pyzbar decode failed: %s", e)
        decoded_objects = []

    if not decoded_objects:
        en = (
            "😕 I couldn’t read any barcode from that picture.\n"
            "Try again with:\n"
            "• A closer shot of the barcode\n"
            "• Good lighting\n"
            "• Barcode straight (not too angled)"
        )
        am = (
            "😕 ከዚያ ፎቶ ማንኛውንም ባርኮድ ማንበብ አልቻልኩም።\n"
            "እንደገና ይሞክሩ በዚህ መልኩ:\n"
            "• ባርኮዱን በቀርበው ምስል ይውሰዱ\n"
            "• በጥሩ ብርሃን ውስጥ\n"
            "• ባርኮዱ ቀጥ እንጂ እጅግ እንዳይዘነጋ"
        )
        await msg.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    # Build reply for all detected barcodes (deduplicate)
    codes: List[str] = []
    for obj in decoded_objects:
        try:
            code = obj.data.decode("utf-8").strip()
        except Exception:
            code = obj.data.decode(errors="ignore").strip()
        if code and code not in codes:
            codes.append(code)

    # Count scans: increment by number of unique codes found
    bot_data = context.bot_data
    bot_data["total_scans"] = bot_data.get("total_scans", 0) + len(codes)

    store = context.user_data.get("store")

    if len(codes) == 1:
        reply_text = build_links_from_code(codes[0], store, lang)
    else:
        # Multiple codes: give individual link blocks
        parts = []
        for c in codes:
            parts.append(build_links_from_code(c, store, lang))
        reply_text = "\n\n---\n\n".join(parts)

    await msg.reply_text(reply_text, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if not is_admin(update):
        en = "⛔ This command is for admins only."
        am = "⛔ ይህ ትእዛዝ ለአስተዳዳሪዎች ብቻ ነው።"
        await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")
        return

    total_scans = context.bot_data.get("total_scans", 0)
    en = f"📊 Total barcodes scanned since last restart: *{{total_scans}}*"
    am = f"📊 ከመጨረሻው መጀመር ጀምሮ የተሸመሩ ባርኮዶች ጠቅላላ ብዛት፦ *{{total_scans}}*"
    await update.message.reply_text(format_text(en, am, lang), parse_mode="Markdown")


def main():
    token = TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("Please set BOT_TOKEN environment variable with your Telegram bot token.")

    if ADMIN_IDS:
        logger.info("Admin IDs set: %s", sorted(ADMIN_IDS))
    else:
        logger.info("No admin IDs configured (ADMIN_IDS is empty).")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("store", store_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ GOJO Clearance Bot v2 (improved) is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
