# debug_xboostbot.py
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Replace token or set BOT_TOKEN env var
import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "7993515747:AAGu9tHn4bnGc8PqEKnw07tlRbdaCHTvq3c")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("xboost-debug")

def main_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Test", callback_data="test")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("start called")
    await update.message.reply_text("✅ Debug bot running", reply_markup=main_menu_keyboard())

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    logger.debug("callback data: %s", q.data)
    await q.edit_message_text(f"Clicked: {q.data}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    await app.initialize()
    await app.start()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())