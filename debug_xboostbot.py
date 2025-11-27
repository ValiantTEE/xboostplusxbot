# debug_xboostbot.py
import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot token (either from env var or fallback)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8521142678:AAGq0NNdHQWC0jB8-SbnSWe7of4bxg-aaOs")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("xboost-debug")

# Simple main menu keyboard
def main_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Test", callback_data="test")]])

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("start called")
    await update.message.reply_text("✅ Debug bot running", reply_markup=main_menu_keyboard())

# Callback query handler
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logger.debug("callback data: %s", query.data)
    await query.edit_message_text(f"Clicked: {query.data}")

# Main entry
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    
    # Only this is needed
    await app.run_polling()