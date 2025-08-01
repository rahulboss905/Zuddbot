import os
import logging
import threading
import time
import sys
from flask import Flask, Response
from pymongo import MongoClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler
)

# Create Flask app for health check
app = Flask(__name__)

@app.route('/health')
def health_check():
    return Response(status=200)

# Enhanced logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot start time for uptime calculation
bot_start_time = time.time()

# Helper function to format uptime
def format_uptime(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
INVITE_LINK = os.getenv("TELEGRAM_INVITE_LINK")
GROUP_LINK = os.getenv("TELEGRAM_GROUP_LINK")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

# Verify environment variables
if not all([TOKEN, CHANNEL_ID, INVITE_LINK, GROUP_LINK, MONGODB_URI, ADMIN_USER_ID]):
    logger.error("Missing required environment variables!")
    missing = [var for var in ["TOKEN", "CHANNEL_ID", "INVITE_LINK", "GROUP_LINK", "MONGODB_URI", "ADMIN_USER_ID"] 
               if not os.getenv(var)]
    logger.error(f"Missing variables: {', '.join(missing)}")
    exit(1)

# MongoDB setup
try:
    client = MongoClient(MONGODB_URI)
    db = client.telegram_bot_db
    users_collection = db.users
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        first_name = update.effective_user.first_name or "Member"
        
        logger.info(f"New user: {user_id} ({username})")
        
        # Check if user exists in DB
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            users_collection.insert_one({
                "user_id": user_id,
                "username": username,
                "first_name": first_name
            })
            logger.info(f"Added new user to DB: {user_id}")
        
        # Check channel membership
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                welcome_message = (
                    "╭───❖━❀🌟❀━❖───╮\n"
                    f"  𝗪𝗲𝗹𝗰𝗼𝗺𝗲, {first_name}! 🎉\n"
                    "╰───❖━❀🌟❀━❖───╯\n\n"
                    "🙏 𝗧𝗵𝗮𝗻𝗸 𝘆𝗼𝘂 𝗳𝗼𝗿 𝘀𝘂𝗯𝘀𝗰𝗿𝗶𝗯𝗶𝗻𝗴 𝘁𝗼 𝗼𝘂𝗿 𝗰𝗵𝗮𝗻𝗻𝗲𝗹!\n"
                    "🎯 𝗪𝗲'𝗿𝗲 𝗴𝗹𝗮𝗱 𝘁𝗼 𝗵𝗮𝘃𝗲 𝘆𝗼𝘂 𝗵𝗲𝗿𝗲.\n\n"
                    "➡️ 𝗧𝗼 𝗴𝗲𝘁 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽 𝗹𝗶𝗻𝗸, 𝗷𝘂𝘀𝘁 𝘀𝗲𝗻𝗱:\n\n"
                    "🔗 `/link`"
                )
                await update.message.reply_text(welcome_message)
                logger.info(f"User {user_id} is verified")
            else:
                await send_verification_request(update, context)
                logger.info(f"User {user_id} needs verification")
        except Exception as e:
            logger.error(f"Membership check error: {e}")
            await send_verification_request(update, context)
    except Exception as e:
        logger.error(f"Start command error: {e}")

async def send_verification_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Join Channel", url=INVITE_LINK)],
        [InlineKeyboardButton("🔄 I've Joined", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    join_message = (
        "⚠️ 𝙋𝙡𝙚𝙖𝙨𝙚 𝙅𝙤𝙞𝙣 𝙊𝙪𝙧 𝘾𝙝𝙖𝙣𝙣𝙚𝙡 𝙩𝙤 𝙐𝙨𝙚 𝙏𝙝𝙞𝙨 𝘽𝙤𝙩!\n\n"
        "📢 𝗢𝘂𝗿 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗽𝗿𝗼𝘃𝗶𝗱𝗲𝘀:\n"
        "— 📝 𝗜𝗺𝗽𝗼𝗿𝘁𝗮𝗻𝘁 𝗨𝗽𝗱𝗮𝘁𝗲𝘀\n"  
        "— 🎁 𝗙𝗿𝗲𝗲 𝗥𝗲𝘀𝗼𝘂𝗿𝗰𝗲𝘀\n"  
        "— 📚 𝗗𝗮𝗶𝗹𝘆 𝗤𝘂𝗶𝘇 & 𝗚𝘂𝗶𝗱𝗮𝗻𝗰𝗲\n"  
        "— ❗ 𝗘𝘅𝗰𝗹𝘂𝘀𝗶𝘃𝗲 𝗖𝗼𝗻𝘁𝗲𝗻𝘁\n\n"
        "✅ 𝘼𝙛𝙩𝙚𝙧 𝙅𝙤𝙞𝙣𝙞𝙣𝙜, 𝙩𝙖𝙥 \"𝐈'𝐯𝐞 𝐉𝐨𝐢𝐧𝐞𝐝\" 𝙗𝙚𝙡𝙤𝙬 �𝙤 𝙘𝙤𝙣𝙩𝙞𝙣𝙪𝙚!"
    )
    
    await update.message.reply_text(
        join_message,
        reply_markup=reply_markup
    )

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        logger.info(f"Membership check callback from user: {user_id}")
        
        try:
            member = await context.bot.get_chat_member(
                chat_id=CHANNEL_ID, 
                user_id=user_id
            )
            if member.status in ['member', 'administrator', 'creator']:
                await query.edit_message_text(
                    "✅ Verification successful!\n"
                    "Use /link to get access to our community group."
                )
                logger.info(f"User {user_id} verified successfully")
            else:
                warning_message = (
                    "❌ 𝙔𝙤𝙪'𝙧𝙚 𝙨𝙩𝙞𝙡𝙡 𝙣𝙤𝙩 𝙞𝙣 𝙩𝙝𝙚 𝙘𝙝𝙖𝙣𝙣𝙚𝙡!\n\n"
                    "😏 𝘿𝙤𝙣'𝙩 𝙗𝙚 𝙤𝙫𝙚𝙧𝙨𝙢𝙖𝙧𝙩 — 𝙩𝙝𝙞𝙨 𝙗𝙤𝙩 𝙬𝙤𝙣'𝙩 𝙬𝙤𝙧𝙠 𝙪𝙣𝙩𝙞𝙡 𝙮𝙤𝙪 𝙟𝙤𝙞𝙣!\n\n"
                    "📢 𝙋𝙡𝙚𝙖𝙨𝙚 𝙟𝙤𝙞𝙣 �𝙝𝙚 𝙘𝙝𝙖𝙣𝙣𝙚𝙡 𝙛𝙞𝙧𝙨𝙩 𝙖𝙣𝙙 𝙩𝙝𝙚𝙣 �𝙧𝙮 𝙖𝙜𝙖𝙞𝙣."
                )
                await query.edit_message_text(warning_message)
                logger.info(f"User {user_id} still not in channel")
        except Exception as e:
            logger.error(f"Callback membership error: {e}")
            await query.edit_message_text("⚠️ Error verifying membership. Please try again.")
    except Exception as e:
        logger.error(f"Callback handler error: {e}")

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Link command from user: {user_id}")
        
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                await update.message.reply_text(
                    f"🔗 Join our group here:\n{GROUP_LINK}"
                )
                logger.info(f"Sent group link to user {user_id}")
            else:
                await send_verification_request(update, context)
                logger.info(f"Sent verification request to user {user_id}")
        except Exception as e:
            logger.error(f"Link command membership check error: {e}")
            await send_verification_request(update, context)
    except Exception as e:
        logger.error(f"Link command error: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Stats command from user: {user_id}")
        
        if str(user_id) != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only!")
            logger.warning(f"Unauthorized stats access attempt by {user_id}")
            return
        
        # Calculate ping
        start_time = time.time()
        test_message = await update.message.reply_text("🏓 Pinging...")
        ping_time = (time.time() - start_time) * 1000  # in milliseconds
        
        # Get user count
        user_count = users_collection.count_documents({})
        
        # Get bot uptime
        uptime_seconds = time.time() - bot_start_time
        uptime_str = format_uptime(uptime_seconds)
        
        # Get versions
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        try:
            mongo_version = db.command("buildInfo")["version"]
        except Exception as e:
            logger.error(f"Failed to get MongoDB version: {e}")
            mongo_version = "Unknown"
        
        # Format stats message
        stats_message = (
            "📊 𝙎𝙩𝙖𝙩𝙨 𝙤𝙛 '𝙐𝙨𝙚𝙧 𝙑𝙚𝙧𝙞𝙛𝙞𝙘𝙖𝙩𝙞𝙤𝙣':\n\n"
            f"🏓 𝙋𝙞𝙣𝙜 𝙋𝙤𝙣𝙜: {ping_time:.2f} ms\n"
            f"👥 𝙏𝙤𝙩𝙖𝙡 𝙐𝙨𝙚𝙧𝙨: {user_count}\n"
            f"⚙️ 𝘽𝙤𝙩 𝙐𝙥𝙩𝙞𝙢𝙚: {uptime_str}\n\n"
            f"🎨 𝙋𝙮𝙩𝙝𝙤𝙣 𝙑𝙚𝙧𝙨𝙞𝙤𝙣: {python_version}\n"
            f"📑 𝙈𝙤𝙣𝙜𝙤 𝙑𝙚𝙧𝙨𝙞𝙤𝙣: {mongo_version}"
        )
        
        await test_message.edit_text(stats_message)
        logger.info(f"Admin stats request: {user_count} users")
        
    except Exception as e:
        logger.error(f"Stats command error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        commands = [
            "/start - Begin using the bot",
            "/link - Get community group link",
            "/help - Show this help message"
        ]
        await update.message.reply_text("\n".join(commands))
        logger.info(f"Help command sent to {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Help command error: {e}")

def main():
    try:
        # Start Flask health check in a separate thread
        flask_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
        )
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Flask health check server started on port 8080")

        # Start Telegram bot
        logger.info("Starting bot application...")
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("link", link))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(check_membership_callback))
        
        logger.info("Bot is now polling...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}")
        exit(1)

if __name__ == '__main__':
    main()
