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
        f"🔢 *Code detected:* `{code}`\n\n"
        f"🧡 *Home Depot search:*\n{home_depot_search}\n\n"
        f"🌐 *Google search:*\n{google_search}\n\n"
        f"{store_line_en}\n\n"
        "👉 Use your Home Depot app or in-store scanner to check final clearance price."
    )

    am = (
        f"🔢 *የተነበበው ባርኮድ ኮድ:* `{code}`\n\n"
        f"🧡 *በ Home Depot ፍለጋ:*\n{home_depot_search}\n\n"
        f"🌐 *በ Google ፍለጋ:*\n{google_search}\n\n"
        f"{store_line_am}\n\n"
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
        f"{store_line_en}\n\n"
        "🗣 Language: English + Amharic (use /lang to change).\n"
        "🏬 Use /store to set your favorite Home Depot store number."
    )

    am = (
        "👋 ወደ *GOJO Home Depot Clearance አጋዥ ቦት* እንኳን ደህና መጡ!\n\n"
        "በክሊራንስ ሽያጭ ጊዜ የእቃ ባርኮድ ፈጣን ምርመራ እርዳታ እሰጣችሁ።\n\n"
        "📸 *የባርኮድ ፎቶ* ይላኩ ወይም\n"
        "⌨️ *የባርኮዱን ቁጥር* ብቻ ይጻፉ (UPC/EAN)."
        f"{store_line_am}\n\n"
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
        "2️⃣ ፎቶውን ወደዚህ ይላኩ ወይም የባርኮዱን ቁጥር ብቻ ይጻፉ።\n"
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
            f"🌐 Current language mode: *{current.upper()}*\n\n"
            "Use one of these:\n"
            "`/lang en` – English only\n" 
            "`/lang am` – Amharic only\n"
            "`/lang bi` – Both English & Amharic"
        )
        am = (
            f"🌐 አሁን የተመረጠው ቋንቋ: *{current.upper()}*\n\n"
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
        am_text = "Another text" 
    else:
        text = "Huge text"
