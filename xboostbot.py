# xboostbot.py
import os
import logging
import aiosqlite
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# --- CONFIG (use env vars on Render or fallback to literal values) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8521142678:AAGq0NNdHQWC0jB8-SbnSWe7of4bxg-aaOs")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5520772144"))
ETH_ADDRESS = os.getenv("ETH_ADDRESS", "0x2eEf07a5728cABC9D9448C028108f163c7B5fb62")
BNB_ADDRESS = os.getenv("BNB_ADDRESS", "0x2eEf07a5728cABC9D9448C028108f163c7B5fb62")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "4jPJjozoYxB8R64Nxygvg255vvyRREnzXr5WZ5742eJN")
DB_PATH = os.getenv("DB_PATH", "xboostplus.db")

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("xboostbot")

# --- CALLBACK DATA ---
CB_SUBSCRIBE = "subscribe"
CB_FOLLOWERS = "followers"
CB_ORDERS = "orders"
CB_ADD_ACCOUNT = "add_account"
CB_HOW_WORKS = "how_works"
CB_SUPPORT = "support"
CB_BACK = "back"
CB_MAIN_MENU = "main_menu"
CB_REMOVE_ACCT = "remove_acct"

# --- PACKAGES / SERVICES ---
SERVICES = {
    "subscribe": {
        "name": "Subscribe / Boost Tweets",
        "packages": [
            ("turbo", "TURBO — $399/Week", 399, "1 Week"),
            ("low", "Low Tier — $349/Month", 349, "1 Month"),
            ("tier1", "Tier 1 — $499/Month", 499, "1 Month"),
            ("tier2", "Tier 2 — $849/Month", 849, "1 Month"),
            ("tier3", "Tier 3 — $1349/Month", 1349, "1 Month"),
            ("tier4", "Tier 4 — $2199/Month", 2199, "1 Month"),
        ]
    },
    "followers": {
        "name": "Buy X Followers",
        "packages": [
            ("blue50", "Starter — 50 Blue Tick Followers — $500", 500, "Instant"),
            ("blue100", "Pro — 100 Blue Tick Followers — $900", 900, "Instant"),
            ("blue200", "Elite — 200 Blue Tick Followers — $1599", 1599, "Instant"),
            ("std500", "Starter — 500 Followers — $250", 250, "Instant"),
            ("std1000", "Growth — 1,000 Followers — $450", 450, "Instant"),
            ("std1500", "Pro — 1,500 Followers — $600", 600, "Instant"),
            ("std2000", "Max — 2,000 Followers — $850", 850, "Instant"),
        ]
    }
}

# --- DB INIT ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                x_handle TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                service TEXT,
                package TEXT,
                price REAL,
                duration TEXT,
                chain TEXT,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """)
        await db.commit()

# --- KEYBOARDS ---
def main_menu_keyboard():
    kb = [
        [InlineKeyboardButton("Subscribe", callback_data=CB_SUBSCRIBE)],
        [InlineKeyboardButton("Buy X Followers", callback_data=CB_FOLLOWERS)],
        [InlineKeyboardButton("Orders", callback_data=CB_ORDERS)],
        [InlineKeyboardButton("Add X Account", callback_data=CB_ADD_ACCOUNT)],
        [InlineKeyboardButton("How XBoostPlus Works", callback_data=CB_HOW_WORKS)],
        [InlineKeyboardButton("Support", url="https://t.me/xboostvip")],
    ]
    return InlineKeyboardMarkup(kb)

def back_and_menu_keyboard():
    kb = [
        [InlineKeyboardButton("Back", callback_data=CB_BACK)],
        [InlineKeyboardButton("Main Menu", callback_data=CB_MAIN_MENU)]
    ]
    return InlineKeyboardMarkup(kb)

def payment_chain_keyboard():
    kb = [
        [InlineKeyboardButton("🟦 Ethereum (ETH)", callback_data="pay_eth")],
        [InlineKeyboardButton("🟨 BNB Smart Chain (BNB)", callback_data="pay_bnb")],
        [InlineKeyboardButton("🟪 Solana (SOL)", callback_data="pay_sol")],
        [InlineKeyboardButton("Back", callback_data=CB_BACK)]
    ]
    return InlineKeyboardMarkup(kb)

# --- UTILS ---
async def get_or_create_user(tid, username):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (tid,))
        row = await cur.fetchone()
        if row:
            return row[0]
        cur = await db.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (tid, username))
        await db.commit()
        return cur.lastrowid

# Navigation helpers
def push_nav(context: ContextTypes.DEFAULT_TYPE, page_id: str, payload: dict = None):
    stack = context.user_data.get("nav_stack", [])
    stack.append({"page": page_id, "payload": payload})
    context.user_data["nav_stack"] = stack

def pop_nav(context: ContextTypes.DEFAULT_TYPE):
    stack = context.user_data.get("nav_stack", [])
    if stack:
        stack.pop()
    return stack[-1] if stack else None

def current_nav(context: ContextTypes.DEFAULT_TYPE):
    stack = context.user_data.get("nav_stack", [])
    return stack[-1] if stack else None

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nav_stack"] = []
    push_nav(context, "main_menu")
    msg = (
        "Welcome to XBoostPlus! 🚀\n\n"
        "Your tweets get boosted automatically right after you post — no extra work needed!\n\n"
        "✅ Get Real followers — no bots, no fakes\n"
        "✅ Authentic engagement that actually lasts\n"
        "✅ Massive reach & millions of impressions\n"
        "✅ Verified users interacting with your content\n"
        "✅ Grow your brand, influence & audience like a true Boss 👑\n\n"
        "💥 NEW: X Followers Packages!\n\n"
        "Please note:\n"
        "Pinned tweets won't be boosted. Pin them after they're boosted.\n"
        "Edited tweets won't be boosted. To fix, delete and post again.\n\n"
        "🚨 PLEASE ONLY TWEET ONCE EVERY 1 HOUR!\n\n"
        "👉 Click a button below to get started."
    )
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

HOW_WORKS_TEXT = (
    "Once you subscribe to XBoostPlus, every time you tweet — including quote retweets — your content gets automatically boosted — no extra work needed!\n\n"
    "✅ Get Real followers — no bots, no fakes\n"
    "✅ Authentic engagement that actually lasts\n"
    "✅ Massive reach & millions of impressions\n"
    "✅ Verified users interacting with your content\n"
    "✅ Grow your brand, influence & audience like a true Boss 👑\n\n"
    "By amplifying your tweet's engagement, XBoostPlus helps you grow your presence on X organically and more efficiently and also helps you get monetized if the X monetization requirements are met.\n\n"
    "Current users of XBoostPlus include Crypto Token Projects, KOLs, Personal Accounts, Businesses."
)

# --- CALLBACK ROUTER ---
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    await get_or_create_user(user.id, user.username)

    # Main menu/back
    if data == CB_MAIN_MENU:
        context.user_data["nav_stack"] = []
        push_nav(context, "main_menu")
        await query.edit_message_text("Main Menu:", reply_markup=main_menu_keyboard())
        return

    if data == CB_BACK:
        prev = pop_nav(context)
        if not prev:
            context.user_data["nav_stack"] = []
            push_nav(context, "main_menu")
            await query.edit_message_text("Main Menu:", reply_markup=main_menu_keyboard())
            return
        page = prev["page"]
        payload = prev.get("payload")
        if page == "select_account_for_service":
            await show_user_accounts_for_service(query, context, payload["service_key"], push_stack=False)
            return
        if page == "service_packages":
            await show_service_packages(query, context, payload["service_key"], push_stack=False)
            return
        if page == "orders_accounts":
            await show_accounts_for_orders(query, context, push_stack=False)
            return
        context.user_data["nav_stack"] = []
        push_nav(context, "main_menu")
        await query.edit_message_text("Main Menu:", reply_markup=main_menu_keyboard())
        return

    # Add account
    if data == CB_ADD_ACCOUNT:
        push_nav(context, "adding_account")
        context.user_data["adding_account"] = True
        await query.edit_message_text("Please send your X handle as username only (no @). Example: user123", reply_markup=back_and_menu_keyboard())
        return

    # Remove account
    if data and data.startswith(f"{CB_REMOVE_ACCT}|"):
        _, acct_id = data.split("|")
        user_rowid = await get_or_create_user(query.from_user.id, query.from_user.username)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (acct_id, user_rowid))
            await db.commit()
        await show_user_accounts_for_service(query, context, service_key="subscribe", push_stack=False)
        return

    # How it works
    if data == CB_HOW_WORKS:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data=CB_MAIN_MENU)]])
        await query.edit_message_text(HOW_WORKS_TEXT, reply_markup=kb)
        return

    # Services
    if data in (CB_SUBSCRIBE, CB_FOLLOWERS):
        service_key = "subscribe" if data == CB_SUBSCRIBE else "followers"
        await show_user_accounts_for_service(query, context, service_key)
        return

    # user selected account
    if data and data.startswith("acctsvc|"):
        _, service_key, acct_id = data.split("|")
        context.user_data["selected_account"] = acct_id
        await show_service_packages(query, context, service_key)
        return

    # package chosen
    if data and data.startswith("pkg|"):
        _, service_key, package_id = data.split("|")
        await handle_package_selected(query, context, service_key, package_id)
        return

    # payment chain
    if data and data.startswith("pay_"):
        chain = data.split("_")[1]
        await show_payment_page(query, context, chain)
        return

    if data == "paid":
        push_nav(context, "awaiting_proof", payload=context.user_data.get("last_package"))
        await query.edit_message_text("Please upload the transaction hash as text or a screenshot as proof of payment.", reply_markup=back_and_menu_keyboard())
        return

    # orders view
    if data == CB_ORDERS:
        await show_accounts_for_orders(query, context)
        return

    if data and data.startswith("orders_acct|"):
        _, account_id = data.split("|")
        await show_orders_for_account(query, context, account_id)
        return

# --- RENDER / SHOW FUNCTIONS ---
async def show_user_accounts_for_service(query, context, service_key, push_stack=True):
    user = query.from_user
    user_rowid = await get_or_create_user(user.id, user.username)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, x_handle FROM accounts WHERE user_id = ?", (user_rowid,))
        rows = await cur.fetchall()
    kb = []
    if rows:
        for rid, handle in rows:
            kb.append([InlineKeyboardButton(str(handle), callback_data=f"acctsvc|{service_key}|{rid}"),
                       InlineKeyboardButton("Remove", callback_data=f"{CB_REMOVE_ACCT}|{rid}")])
    kb.append([InlineKeyboardButton("Add X Account", callback_data=CB_ADD_ACCOUNT)])
    kb.append([InlineKeyboardButton("Main Menu", callback_data=CB_MAIN_MENU)])
    if push_stack:
        push_nav(context, "select_account_for_service", payload={"service_key": service_key})
    await query.edit_message_text("📋 To continue select an X (Twitter) account below:", reply_markup=InlineKeyboardMarkup(kb))

async def show_service_packages(query, context, service_key, push_stack=True):
    svc = SERVICES.get(service_key)
    if service_key == "subscribe":
        template = (
            "💰 Engagement Boost Tiers\n\n"
            "⚡️ Tier TURBO – Flash Fame Pack\n"
            "(Per Post / Max 1 per Hour)\n"
            "10 Comments Minimum\n90 Likes Minimum\n30 Retweets Minimum\n5 Bookmarks Minimum\n5K Views Minimum\n"
            "💰 $399 / Week (1 Week Only)\n\n"
            "🔵 Low Tier – The Small Pack\n"
            "(Per Post / Max 1 per Hour)\n"
            "3 Comments Minimum\n15 Likes Minimum\n5 Retweets Minimum\n1 Bookmarks Minimum\n500 Views Minimum\n"
            "💰 $349 / Month\n\n"
            "✨ Tier 1 – The Starter Pack (For Normies)\n"
            "(Per Post / Max 1 per Hour)\n"
            "5 Comments Minimum\n45 Likes Minimum\n15 Retweets Minimum\n3 Bookmarks Minimum\n2.5K Views Minimum\n"
            "💰 $449 / Month\n\n"
            "✨ Tier 2 – Influencer's Little Brother\n"
            "(Per Post / Max 1 per Hour)\n"
            "10 Comments Minimum\n90 Likes Minimum\n30 Retweets Minimum\n5 Bookmarks Minimum\n5K Views Minimum\n"
            "💰 $849 / Month\n\n"
            "✨ Tier 3 – Certified Clout Chaser\n"
            "(Per Post / Max 1 per Hour)\n"
            "15 Comments Minimum\n180 Likes Minimum\n60 Retweets Minimum\n10 Bookmarks Minimum\n10K Views Minimum\n"
            "💰 $1349 / Month\n\n"
            "✨ Tier 4 – CHAD CT Wanderer (Boss Mode)\n"
            "(Per Post / Max 1 per Hour)\n"
            "20 Comments Minimum\n360 Likes Minimum\n120 Retweets Minimum\n20 Bookmarks Minimum\n20K Views Minimum\n"
            "Dedicated VIP chat room\nThreads included!\n"
            "💰 $2199 / Month\n\n"
            "Note: All engagements are per tweet/quote retweet, applied on every tweet you post while subscribed to any Tiers\n"
            "Note: Please only tweet once per hour for max engagement."
        )
    else:
        template = (
            "💎 X FOLLOWERS PACKAGES\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🟦 Verified (Blue Tick) Followers\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "🔹 Starter — 50 Followers — $500\n"
            "🔹 Pro — 100 Followers — $900\n"
            "🔹 Elite — 200 Followers — $1599\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚡️ Standard X Followers\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "⚡️ Starter — 500 Followers — $250\n"
            "⚡️ Growth — 1,000 Followers — $450\n"
            "⚡️ Pro — 1,500 Followers — $600\n"
            "⚡️ Max — 2,000 Followers — $850\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "💰 BUNDLE OFFERS\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "🔵 Influencer Starter — 50 Blue Tick + 500 Normal — $700\n"
            "🔵 Influencer Pro — 100 Blue Tick + 1,000 Normal — $1100\n"
            "🔵 Influencer Elite — 200 Blue Tick + 2,000 Normal — $2000\n\n"
            "⏳ ORDERS ARE PROCESSED GRADUALLY AND MAY TAKE UP TO 1-48HOURS TO COMPLETE.\n\n"
            "💡 FOLLOWERS ARE PERMANENT AND WON'T DROP OVER TIME — WE USE LONG-TERM, MAINTAINED ACCOUNTS."
        )

    kb = [[InlineKeyboardButton(p[1], callback_data=f"pkg|{service_key}|{p[0]}")] for p in svc["packages"]]
    kb.append([InlineKeyboardButton("Back", callback_data=CB_BACK)])
    if push_stack:
        push_nav(context, "service_packages", payload={"service_key": service_key})
    await query.edit_message_text(template, reply_markup=InlineKeyboardMarkup(kb))

async def handle_package_selected(query, context, service_key, package_id):
    svc = SERVICES.get(service_key)
    pkg = next((p for p in svc["packages"] if p[0] == package_id), None)
    last_account = context.user_data.get("selected_account")
    context.user_data["last_package"] = {
        "service_key": service_key,
        "package_id": package_id,
        "package_name": pkg[1],
        "price_usd": pkg[2],
        "duration": pkg[3],
        "account_id": last_account
    }
    push_nav(context, "package_selected", payload={"service_key": service_key, "package_id": package_id})
    header = f"{'🚀 Engagement Boost' if service_key=='subscribe' else '👥 Followers'} — {pkg[1]}"
    msg = (
        f"{header}\n\n"
        f"Duration: {pkg[3]}\n"
        f"Price: `${pkg[2]}`\n\n"
        "Choose which blockchain to pay with:"
    )
    await query.edit_message_text(msg, reply_markup=payment_chain_keyboard())

async def show_payment_page(query, context, chain):
    last_package = context.user_data.get("last_package")
    if not last_package:
        await query.edit_message_text("No package selected.", reply_markup=main_menu_keyboard())
        return

    if chain == "eth":
        address = ETH_ADDRESS
        chain_name = "Ethereum (ETH)"
        chain_icon = "🟦"
    elif chain == "bnb":
        address = BNB_ADDRESS
        chain_name = "BNB Smart Chain (BNB)"
        chain_icon = "🟨"
    else:
        address = SOL_ADDRESS
        chain_name = "Solana (SOL)"
        chain_icon = "🟪"

    push_nav(context, "payment_page", payload={"chain": chain, "package": last_package})
    context.user_data["payment_chain"] = chain

    msg = (
        f"💳 *Payment Required*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 *Package:*  {last_package['package_name']}\n"
        f"📆 *Duration:* {last_package['duration']}\n"
        f"💲 *Amount:*   `${last_package['price_usd']}`\n"
        f"{chain_icon} *Chain:* {chain_name}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 *Payment Address*\n"
        f"Send the exact amount to the address below:\n"
        f"```\n{address}\n```\n\n"
        f"⚠️ *Make sure the network you select matches the chain above.*\n"
        f"After payment, click *I've Paid* and upload your TX hash or a screenshot."
    )

    kb = [
        [InlineKeyboardButton("I've Paid", callback_data="paid")],
        [InlineKeyboardButton("Back", callback_data=CB_BACK)]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- ORDERS / VIEW ---
async def show_accounts_for_orders(query, context, push_stack=True):
    user = query.from_user
    user_rowid = await get_or_create_user(user.id, user.username)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, x_handle FROM accounts WHERE user_id = ?", (user_rowid,))
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No X accounts found. Add one first.", reply_markup=main_menu_keyboard())
        return
    kb = [[InlineKeyboardButton(str(h), callback_data=f"orders_acct|{rid}")] for rid, h in rows]
    kb.append([InlineKeyboardButton("Back", callback_data=CB_BACK)])
    if push_stack:
        push_nav(context, "orders_accounts")
    await query.edit_message_text("📋 Select X Account to view orders:", reply_markup=InlineKeyboardMarkup(kb))

async def show_orders_for_account(query, context, account_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, service, package, price, duration, chain, status, created_at
            FROM orders WHERE account_id = ?
            ORDER BY id DESC
        """, (account_id,))
        orders = await cur.fetchall()
    if not orders:
        await query.edit_message_text("No orders found for this account.", reply_markup=back_and_menu_keyboard())
        return
    msg_lines = ["📋 Orders for this X account:\n"]
    for idx, (oid, service, package, price, duration, chain, status, created_at) in enumerate(orders, 1):
        msg_lines.append(f"{idx}. Order ID: {oid}\n   Package: {package}\n   Service: {service}\n   Price: ${price}\n   Duration: {duration}\n   Chain: {chain}\n   Status: {status}\n   Created: {created_at}\n")
    msg_text = "\n".join(msg_lines)
    await query.edit_message_text(msg_text, reply_markup=back_and_menu_keyboard())

# --- ADD ACCOUNT (text) ---
async def handle_add_account_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("adding_account"):
        return
    x_handle = update.message.text.strip().replace("@", "")
    user_rowid = await get_or_create_user(update.message.from_user.id, update.message.from_user.username)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO accounts (user_id, x_handle) VALUES (?, ?)", (user_rowid, x_handle))
        await db.commit()
    context.user_data["adding_account"] = False
    pop_nav(context)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Subscribe Now", callback_data=CB_SUBSCRIBE)],
        [InlineKeyboardButton("Buy X Followers", callback_data=CB_FOLLOWERS)],
        [InlineKeyboardButton("View Connected Accounts", callback_data=CB_ORDERS)],
        [InlineKeyboardButton("Main Menu", callback_data=CB_MAIN_MENU)]
    ])
    await update.message.reply_text(f"✅ Your account was added successfully! Saved as x.com/{x_handle}", reply_markup=kb)

# --- PAYMENT PROOF (text tx) ---
async def handle_tx_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_package = context.user_data.get("last_package")
    if not last_package:
        await handle_add_account_text(update, context)
        return
    chain = context.user_data.get("payment_chain")
    tx_hash = update.message.text.strip()
    created_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO orders (user_id, account_id, service, package, price, duration, chain, tx_hash, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            update.message.from_user.id,
            last_package.get("account_id"),
            last_package.get("service_key"),
            last_package.get("package_name"),
            last_package.get("price_usd"),
            last_package.get("duration"),
            chain,
            tx_hash,
            "pending",
            created_at
        ))
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        order_id = row[0] if row else None

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💰 New payment submitted\n"
                f"User: @{update.message.from_user.username} ({update.message.from_user.id})\n"
                f"Order ID: {order_id}\n"
                f"Package: {last_package['package_name']}\n"
                f"Amount: ${last_package['price_usd']}\n"
                f"Chain: {chain}\n"
                f"TX: `{tx_hash}`"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        logger.exception("Failed to notify admin about TX")

    context.user_data.pop("last_package", None)
    context.user_data.pop("payment_chain", None)
    pop_nav(context)
    await update.message.reply_text("✅ Payment submitted. Admin will verify and update status shortly.", reply_markup=main_menu_keyboard())

# --- PAYMENT PROOF (photo) ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_package = context.user_data.get("last_package")
    if not last_package:
        await update.message.reply_text("No active payment found. Use the menus to place an order.", reply_markup=main_menu_keyboard())
        return
    file_id = update.message.photo[-1].file_id
    chain = context.user_data.get("payment_chain")
    created_at = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO orders (user_id, account_id, service, package, price, duration, chain, tx_hash, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            update.message.from_user.id,
            last_package.get("account_id"),
            last_package.get("service_key"),
            last_package.get("package_name"),
            last_package.get("price_usd"),
            last_package.get("duration"),
            chain,
            file_id,
            "pending",
            created_at
        ))
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        order_id = row[0] if row else None

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💰 New payment screenshot submitted\n"
                f"User: @{update.message.from_user.username} ({update.message.from_user.id})\n"
                f"Order ID: {order_id}\n"
                f"Package: {last_package['package_name']}\n"
                f"Amount: ${last_package['price_usd']}\n"
                f"Chain: {chain}\n"
                f"File ID: {file_id}"
            )
        )
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=f"Screenshot from @{update.message.from_user.username}")
    except Exception:
        logger.exception("Failed to notify admin about photo")

    context.user_data.pop("last_package", None)
    context.user_data.pop("payment_chain", None)
    pop_nav(context)
    await update.message.reply_text("✅ Payment submitted. Admin will verify and update status shortly.", reply_markup=main_menu_keyboard())

# --- MESSAGE ROUTER ---
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("adding_account"):
        await handle_add_account_text(update, context)
        return
    nav = current_nav(context)
    if nav and nav.get("page") in ("awaiting_proof", "payment_page", "package_selected"):
        await handle_tx_text(update, context)
        return
    await update.message.reply_text("Please use the menu buttons.", reply_markup=main_menu_keyboard())

# --- ADMIN COMMANDS ---
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, user_id, package, price, chain, status, created_at FROM orders WHERE status = 'pending' ORDER BY id DESC")
        rows = await cur.fetchall()
    if not rows:
        await update.message.reply_text("No pending orders.")
        return
    text = "Pending orders:\n\n"
    for r in rows[:50]:
        oid, uid, package, price, chain, status, created_at = r
        text += f"ID: {oid} | User: {uid} | {package} | ${price} | {chain} | {created_at}\n"
    await update.message.reply_text(text)

async def admin_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /complete <order_id>")
        return
    try:
        oid = int(args[0])
    except ValueError:
        await update.message.reply_text("Order id must be numeric")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (oid,))
        await db.commit()
        cur = await db.execute("SELECT user_id FROM orders WHERE id = ?", (oid,))
        row = await cur.fetchone()
    if row:
        user_id = row[0]
        try:
            await context.bot.send_message(chat_id=user_id, text=f"✅ Your order {oid} has been marked as completed by admin.")
        except Exception:
            pass
    await update.message.reply_text(f"Order {oid} marked completed.")

# --- MAIN & STARTUP ---
# --- MAIN & STARTUP ---
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("complete", admin_complete))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    logger.info("Starting XBoostPlus bot...")

    await app.bot.delete_webhook(drop_pending_updates=True)

    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    import sys
    import asyncio

    try:
        # Use run_polling() directly without asyncio.run()
        import nest_asyncio
        nest_asyncio.apply()  # Allows nested event loops (fixes macOS / Jupyter issues)
    except ImportError:
        pass

    import logging
    logging.basicConfig(level=logging.INFO)

    import xboostbot  # or your module name if needed

    # Run the main bot
    asyncio.get_event_loop().run_until_complete(main())