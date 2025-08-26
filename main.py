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
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# Create Flask app for health check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running", 200

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
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
TUTORIAL_VIDEO_LINK = os.getenv("TUTORIAL_VIDEO_LINK", "https://youtube.com/shorts/UhccqnGY3PY?si=1aswpXBhcFP8L8tM")

# Verify environment variables
if not all([TOKEN, CHANNEL_ID, MONGODB_URI, ADMIN_USER_ID]):
    logger.error("Missing required environment variables!")
    missing = [var for var in ["TOKEN", "CHANNEL_ID", "MONGODB_URI", "ADMIN_USER_ID"] 
               if not os.getenv(var)]
    logger.error(f"Missing variables: {', '.join(missing)}")
    exit(1)

# MongoDB setup
try:
    client = MongoClient(MONGODB_URI)
    db = client.telegram_bot_db
    users_collection = db.users
    custom_commands_collection = db.custom_commands
    logger.info("Connected to MongoDB successfully")
    
    # Create index for command names
    custom_commands_collection.create_index("command", unique=True)
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    exit(1)

async def is_owner(user_id: int) -> bool:
    return str(user_id) == ADMIN_USER_ID

async def generate_invite_link(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Generate a temporary invite link that expires in 5 minutes"""
    try:
        # Create an invite link that expires in 5 minutes
        expire_date = int(time.time()) + 300  # 5 minutes from now
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            expire_date=expire_date,
            member_limit=1  # Single use link
        )
        return invite_link.invite_link
    except Exception as e:
        logger.error(f"Failed to generate invite link: {e}")
        # Fallback to a basic link if generation fails
        return f"https://t.me/{CHANNEL_ID}"

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
                "first_name": first_name,
                "date_added": time.time()
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
                    "➡️ 𝗨𝘀𝗲 𝘁𝗵𝗲𝘀𝗲 𝗰𝗼𝗺𝗮𝗻𝗱𝘀:\n\n"
                    "📚 `/lecture` - Show all available lecture groups\n"
                    "❓ `/help` - Get help with bot commands"
                )
                await update.message.reply_text(
                    welcome_message,
                    protect_content=True
                )
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
    # Generate a new temporary invite link
    invite_link = await generate_invite_link(context)
    
    keyboard = [
        [InlineKeyboardButton("✅ Join Channel", url=invite_link)],
        [InlineKeyboardButton("🔄 I've Joined", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    join_message = (
        "⚠️ Please Join Our Channel to Use This Bot!\n\n"
        "📢 Our channel provides:\n"
        "— 📝 Important Updates\n"  
        "— 🎁 Free Resources\n"  
        "— 📚 Daily Quiz & Guidance\n"  
        "— ❗ Exclusive Content\n\n"
        "✅ After Joining, tap \"I've Joined\" below to continue!\n\n"
        "🔒 This invite link expires in 5 minutes"
    )
    
    await update.message.reply_text(
        join_message,
        reply_markup=reply_markup,
        protect_content=True
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
                    "Use /lecture to see all available groups or /help for assistance."
                )
                logger.info(f"User {user_id} verified successfully")
            else:
                warning_message = (
                    "❌ You're still not in the channel!\n\n"
                    "Please join the channel first and then try again."
                )
                await query.edit_message_text(warning_message)
                logger.info(f"User {user_id} still not in channel")
        except Exception as e:
            logger.error(f"Callback membership error: {e}")
            await query.edit_message_text("⚠️ Error verifying membership. Please try again.")
    except Exception as e:
        logger.error(f"Callback handler error: {e}")

# Unified lecture command to list all custom commands with descriptions
async def lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Lecture command from user: {user_id}")
        
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                await send_verification_request(update, context)
                logger.info(f"Sent verification request to user {user_id}")
                return
        except Exception as e:
            logger.error(f"Lecture command membership check error: {e}")
            await send_verification_request(update, context)
            return
        
        # Get all custom commands
        commands = list(custom_commands_collection.find({}))
        
        if not commands:
            await update.message.reply_text(
                "📚 No lecture groups available yet. Check back later!",
                protect_content=True
            )
            return
            
        # Create response with all commands and descriptions
        response = "📚 Available Lecture Groups:\n\n"
        for cmd in commands:
            response += f"🔹 /{cmd['command']} - {cmd.get('description', 'No description')}\n\n"
        
        response += "\nUse any command above to join its group!"
        
        await update.message.reply_text(
            response,
            protect_content=True
        )
        logger.info(f"Sent lecture list to user {user_id}")
        
    except Exception as e:
        logger.error(f"Lecture command error: {e}")

# Admin command to add new lecture group command with description
async def add_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Addlecture command from user: {user_id}")
        
        if not await is_owner(user_id):
            await update.message.reply_text("❌ This command is for bot owner only!")
            logger.warning(f"Unauthorized addlecture attempt by {user_id}")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ Please provide command name, link, and description.\n"
                "Usage: /addlecture <command_name> <link> <description>\n"
                "Example: /addlecture maths https://t.me/mathsgroup \"Mathematics study group\""
            )
            return
        
        command_name = context.args[0].lower().strip()
        group_link = context.args[1].strip()
        
        # Combine all remaining arguments as description
        description = ' '.join(context.args[2:])
        
        # Validate command name
        if command_name.startswith('/'):
            command_name = command_name[1:]
            
        if not command_name.isalpha():
            await update.message.reply_text("❌ Command name must contain only letters!")
            return
            
        # Save to database with description
        custom_commands_collection.update_one(
            {"command": command_name},
            {"$set": {
                "link": group_link,
                "description": description
            }},
            upsert=True
        )
        
        await update.message.reply_text(
            f"✅ Lecture group command added successfully!\n\n"
            f"🔹 Command: /{command_name}\n"
            f"🔗 Link: {group_link}\n"
            f"📝 Description: {description}\n\n"
            f"Users can now use /{command_name} to join this group."
        )
        logger.info(f"Added lecture command: /{command_name} -> {group_link} ({description})")
        
    except Exception as e:
        logger.error(f"Addlecture command error: {e}")
        await update.message.reply_text("⚠️ Failed to add lecture command. Please try again.")

# Admin command to remove lecture command
async def remove_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Removelecture command from user: {user_id}")
        
        if not await is_owner(user_id):
            await update.message.reply_text("❌ This command is for bot owner only!")
            logger.warning(f"Unauthorized removelecture attempt by {user_id}")
            return
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Please provide a command to remove.\n"
                "Usage: /removelecture <command_name>\n"
                "Example: /removelecture maths"
            )
            return
        
        command_name = context.args[0].lower().strip()
        
        # Remove from database
        result = custom_commands_collection.delete_one({"command": command_name})
        
        if result.deleted_count > 0:
            await update.message.reply_text(f"✅ Command /{command_name} has been removed.")
            logger.info(f"Removed lecture command: /{command_name}")
        else:
            await update.message.reply_text(f"❌ Command /极速赛车群} not found.")
            logger.info(f"Attempted to remove non-existent command: /{command_name}")
        
    except Exception as e:
        logger.error(f"Removelecture command error: {e}")
        await update.message.reply_text("⚠️ Failed to remove lecture command. Please try again.")

# Handler for custom lecture commands - UPDATED WITH TUTORIAL VIDEO
async def lecture_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        command = update.message.text.split()[0][1:].lower()  # Remove slash
        
        logger.info(f"Lecture command from user: {user_id} - /{command}")
        
        # Find command in database
        cmd_data = custom_commands_collection.find_one({"command": command})
        if not cmd_data:
            return  # Not a lecture command
        
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                # Create inline buttons for group link and tutorial
                keyboard = [
                    [InlineKeyboardButton(f"👉 Join {command.capitalize()} Group 👈", url=cmd_data["link"])],
                    [InlineKeyboardButton("📺 Watch Tutorial Video", url=TUTORIAL_VIDEO_LINK)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get description or use default
                description = cmd_data.get("description", f"Join the {command} group")
                
                await update.message.reply_text(
                    f"📚 {description}\n\n"
                    "Click the button below to join the group:\n"
                    "Need help joining? Watch the tutorial video!",
                    reply_markup=reply_markup,
                    protect_content=True
                )
                logger.info(f"Sent lecture group link to user {user_id} for /{command}")
            else:
                await send_verification_request(update, context)
                logger.info(f"Sent verification request to user极速赛车群}")
        except Exception as e:
            logger.error(f"Lecture command membership check error: {e}")
            await send_verification_request(update, context)
    except Exception as e:
        logger.error极速赛车群}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Stats command from user: {user_id}")
        
        if not await is_owner(user_id):
            await update.message.reply_text("❌ This command is for bot owner only!")
            logger.warning(f"Unauthorized stats access attempt by {user_id}")
            return
        
        # Calculate ping
        start_time = time.time()
        test_message = await update.message.reply_text("🏓 Pinging...")
        ping_time = (time.time() - start_time) * 1000  # in milliseconds
        
极速赛车群} user_count = users_collection.count_documents({})
        
        # Get lecture command count
        command_count = custom_commands极速赛车群}
        
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
            "📊 Bot Statistics:\n\n"
            f"🏓 Ping: {ping_time:.2f} ms\n"
            f"👥 Total Users: {user_count}\n"
            f"📚 Lecture Groups: {command_count}\n"
            f"⏱️ Uptime: {uptime_str}\极速赛车群}"
            f"🐍 Python: {python_version}\n"
            f"🍃 MongoDB: {mongo_version}"
        )
        
        await test_message.edit_text(stats_message)
        logger.info(f"Admin stats request: {user_count} users, {command_count} commands")
        
    except Exception as e:
        logger.error(f"Stats command error: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        logger.info(f"Broadcast command from user: {user_id}")
        
        if not await is_owner(user_id):
            await update.message.reply_text("❌ This command is for bot owner only!")
            logger.warning(f"Unauthorized broadcast attempt by {user_id}")
            return
        
        # Check if the message is a reply to another message
        if not update.message.reply_to_message and not context.args:
            await update.message.reply_text(
                "⚠️ Please provide a message to broadcast or reply to a message.\n"
                "Usage: /broadcast <your message> OR reply to a message with /broadcast"
            )
            return
        
        total_users = users_collection.count_documents({})
        success_count = 0
        failed_count = 0
        
        progress_msg = await update.message.reply_text(
            f"📢 Starting broadcast to {total_users} users...\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {failed_count}"
        )
        
        # Get the message to broadcast
        if update.message.reply_to_message:
            # Broadcast the replied message with all its content
            replied_message = update.message.reply_to_message
            broadcast_content = replied_message
            is_reply = True
        else:
            # Broadcast text from command arguments
            broadcast_content = ' '.join(context.args)
            is_reply = False
        
        for user in users_collection.find():
            try:
                if is_reply:
                    # Forward the replied message with all its media/content
                    await broadcast_content.forward(
                        chat_id=user['user_id'],
                        protect_content=True
                    )
                else:
                    # Send text message
                    await context.bot.send_message(
                        chat_id=user['user_id'],
                        text=broadcast_content,
                        protect_content=True
                    )
                success_count += 1
                
                # Update progress every 10 sends
                if (success_count + failed_count) % 10 == 0:
                    await progress_msg.edit_text(
                        f"📢 Broadcasting to {total_users} users...\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {failed_count}"
                    )
                    
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send to user {user['user_id']}: {e}")
        
        await progress_msg.edit_text(
            f"🎉 Broadcast completed!\n"
            f"📢 Sent to: {total_users} users\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {failed_count}"
        )
        logger.info(f"Broadcast completed. Success: {success_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Broadcast command error: {e}")
        await update.message.reply_text("⚠️ An error occurred during broadcast.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        is_admin = await is_owner(user_id)
        
        commands = [
            "/start - Begin using the bot",
            "/lecture - Show all lecture groups",
            "/help - Show this help message"
        ]
        
        # Create inline button for tutorial video
        tutorial_button = InlineKeyboardButton(
            "📺 Watch Tutorial Video", 
            url=TUTORIAL_VIDEO_LINK
        )
        reply_markup = InlineKeyboardMarkup([[tutorial_button]])
        
        if is_admin:
            admin_commands = [
                "\n\n👑 Admin Commands:",
                "/addlecture <name> <link> <description> - Add new lecture group",
                "/removelecture <name极速赛车群} - Remove a lecture group",
                "/stats - View bot statistics",
                "/broadcast <message> - Send message to all users (or reply to a message)"
            ]
            commands.extend(admin_commands)
        
        help_message = "\n".join(commands) + "\n\nNeed help using the bot? Watch our tutorial video!"
        
        await update.message.reply_text(
            help_message,
            reply_markup=reply_markup,
            protect_content=True
        )
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
        application.add_handler(CommandHandler("lecture", lecture))
        application.add_handler(CommandHandler("addlecture", add_lecture))
        application.add_handler(CommandHandler("removelecture", remove_lecture))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(check_membership_callback))
        
        # Add handler for custom lecture commands
        application.add_handler(MessageHandler(filters.COMMAND, lecture_command_handler))
        
        logger.info("Bot is now polling...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}")
        exit(1)

if __name__ == '__main__':
    main()