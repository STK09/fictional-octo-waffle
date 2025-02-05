import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# Database connection
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]
requests_collection = db["requests"]

# Track bot start time
BOT_START_TIME = datetime.now()
temporary_passwords = {}

# Helper function to format time
def format_time(minutes):
    days, rem = divmod(minutes, 1440)
    hours, minutes = divmod(rem, 60)
    time_str = []
    if days: time_str.append(f"{days} day{'s' if days > 1 else ''}")
    if hours: time_str.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes: time_str.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    return " ".join(time_str)

# Helper function to check if user is authorized
def is_authorized(user_id):
    return users_collection.find_one({"user_id": user_id, "authorized": True}) is not None

# Unauthorized message
def unauthorized_message(update, context):
    update.message.reply_text(
        "🚫 Unauthorized User\n\n"
        "Use /login (your_password) to access this bot.",
        parse_mode=ParseMode.HTML,
    )

# /login command
def login(update, context):
    user_id = update.effective_user.id
    if is_authorized(user_id):
        update.message.reply_text("✅ You are already logged in!", parse_mode=ParseMode.HTML)
        return

    if len(context.args) != 1:
        update.message.reply_text("❌ Invalid Usage! Use: /login (your_password)", parse_mode=ParseMode.HTML)
        return

    password = context.args[0]
    temp_password = temporary_passwords.get(user_id)

    if temp_password and password == temp_password["password"]:
        # Grant access and remove temporary password
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"authorized": True, "expires_at": None, "username": update.effective_user.username}},
            upsert=True,
        )
        del temporary_passwords[user_id]
        update.message.reply_text("✅ Login Successful!", parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text("❌ Invalid Password!", parse_mode=ParseMode.HTML)

# /auth command (Owner only)
def auth(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) != 2:
        update.message.reply_text("❌ Invalid Usage! Use: /auth (user_id) (time_in_minutes)", parse_mode=ParseMode.HTML)
        return

    try:
        user_id = int(context.args[0])
        time_in_minutes = int(context.args[1])
        password = str(random.randint(10000000, 99999999))
        expiry_time = datetime.now() + timedelta(minutes=time_in_minutes)

        temporary_passwords[user_id] = {"password": password, "expires_at": expiry_time}

        update.message.reply_text(
            f"✅ Temporary Password: {password}\nExpires in: {format_time(time_in_minutes)}",
            parse_mode=ParseMode.HTML,
        )
    except ValueError:
        update.message.reply_text("❌ Invalid user_id or time format!", parse_mode=ParseMode.HTML)

# /unauth command (Owner only)
def unauth(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) != 1:
        update.message.reply_text("❌ Invalid Usage! Use: /unauth (user_id)", parse_mode=ParseMode.HTML)
        return

    user_id = int(context.args[0])
    users_collection.update_one({"user_id": user_id}, {"$set": {"authorized": False}})
    update.message.reply_text(f"✅ User {user_id} unauthorized!", parse_mode=ParseMode.HTML)

# /stats command (Owner only)
def stats(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    authorized_count = users_collection.count_documents({"authorized": True})
    uptime = datetime.now() - BOT_START_TIME

    update.message.reply_text(
        f"📊 Bot Stats\n\n"
        f"👥 Authorized Users: {authorized_count}\n"
        f"⏱ Uptime: {str(uptime).split('.')[0]}",
        parse_mode=ParseMode.HTML,
    )

# /req command for authorized users
def req(update, context):
    if not is_authorized(update.effective_user.id):
        unauthorized_message(update, context)
        return

    if len(context.args) == 0:
        update.message.reply_text("❌ Invalid Usage! Use: /req (request_text)", parse_mode=ParseMode.HTML)
        return

    request_text = " ".join(context.args)
    owner_message = (
        f"📥 New Request\n\n"
        f"👤 From: @{update.effective_user.username} ({update.effective_user.id})\n"
        f"📝 Request: {request_text}"
    )
    requests_collection.insert_one({"user_id": update.effective_user.id, "request": request_text, "timestamp": datetime.now()})

    context.bot.send_message(chat_id=OWNER_ID, text=owner_message, parse_mode=ParseMode.HTML)
    update.message.reply_text("✅ Your request has been successfully submitted!", parse_mode=ParseMode.HTML)

# Main function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("unauth", unauth))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("req", req))

    # Message handler for unauthorized users
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unauthorized_message))

    # Start polling the bot
    application.run_polling()

if __name__ == "__main__":
    main()
