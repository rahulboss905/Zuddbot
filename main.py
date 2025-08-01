import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
INVITE_LINK = os.getenv("TELEGRAM_INVITE_LINK")
GROUP_LINK = os.getenv("TELEGRAM_GROUP_LINK")
MONGODB_URI = os.getenv("MONGODB_URI")

# MongoDB setup
client = MongoClient(MONGODB_URI)
db = client.telegram_bot_db
users_collection = db.users

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # Check if user exists in DB
    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "first_name": first_name
        })
    
    # Check channel membership
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await update.message.reply_text(
                f"👋 Welcome {first_name}! You're verified!\n"
                "Use /link to get access to our community group."
            )
        else:
            await send_verification_request(update, context)
    except Exception as e:
        logging.error(f"Error checking membership: {e}")
        await send_verification_request(update, context)

async def send_verification_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Join Channel", url=INVITE_LINK)],
        [InlineKeyboardButton("🔄 I've Joined", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Please join our channel to use this bot!\n"
        "After joining, click 'I've Joined' to verify.",
        reply_markup=reply_markup
    )

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID, 
            user_id=query.from_user.id
        )
        if member.status in ['member', 'administrator', 'creator']:
            await query.edit_message_text(
                "✅ Verification successful!\n"
                "Use /link to get access to our community group."
            )
        else:
            await query.edit_message_text(
                "❌ You're still not in the channel!\n"
                "Please join first and try again."
            )
    except Exception as e:
        logging.error(f"Callback error: {e}")
        await query.edit_message_text("⚠️ Error verifying membership. Please try again.")

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await update.message.reply_text(
                f"🔗 Join our group here:\n{GROUP_LINK}"
            )
        else:
            await send_verification_request(update, context)
    except Exception as e:
        logging.error(f"Link command error: {e}")
        await send_verification_request(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_USER_ID")):
        await update.message.reply_text("❌ This command is for admins only!")
        return
    
    user_count = users_collection.count_documents({})
    await update.message.reply_text(f"📊 Total unique users: {user_count}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Begin using the bot",
        "/link - Get community group link",
        "/help - Show this help message"
    ]
    await update.message.reply_text("\n".join(commands))

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", link))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(check_membership_callback))
    
    application.run_polling()

if __name__ == '__main__':
    main()