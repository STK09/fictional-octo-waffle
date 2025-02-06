import os
import time
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message
from uvloop import install

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# Initialize Pyrogram Client
app = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN).start()

install()

# Database connection
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]
requests_collection = db["requests"]

# Track bot start time
BOT_START_TIME = datetime.now()
temporary_passwords = {}

# Helper function: Format time into human-readable format
def format_time(minutes):
    days, rem = divmod(minutes, 1440)
    hours, minutes = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m".strip()

# Helper function: Check if user is authorized
def is_authorized(user_id):
    return users_collection.find_one({"user_id": user_id, "authorized": True}) is not None

# Unauthorized message
async def unauthorized_message(client, message):
    await message.reply_text(
        "🚫 <b>Unauthorized User</b>\n\n"
        "Use <code>/login your_password</code> to access this bot.",
        parse_mode="html",
    )

# /login command
@app.on_message(filters.command("login"))
async def login(client, message: Message):
    user_id = message.from_user.id
    if is_authorized(user_id):
        await message.reply_text("✅ <b>You are already logged in!</b>", parse_mode="html")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.reply_text("❌ <b>Invalid Usage!</b> Use: <code>/login your_password</code>", parse_mode="html")
        return

    password = parts[1]
    temp_password = temporary_passwords.get(user_id)

    if temp_password and password == temp_password["password"]:
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"authorized": True, "expires_at": None, "username": message.from_user.username}},
            upsert=True,
        )
        del temporary_passwords[user_id]
        await message.reply_text("✅ <b>Login Successful!</b>", parse_mode="html")
    else:
        await message.reply_text("❌ <b>Invalid Password!</b>", parse_mode="html")

# /auth command (Owner only)
@app.on_message(filters.command("auth") & filters.user(OWNER_ID))
async def auth(client, message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply_text("❌ <b>Invalid Usage!</b> Use: <code>/auth user_id time_in_minutes</code>", parse_mode="html")
        return

    try:
        user_id = int(parts[1])
        time_in_minutes = int(parts[2])
        password = str(random.randint(10000000, 99999999))
        expiry_time = datetime.now() + timedelta(minutes=time_in_minutes)

        temporary_passwords[user_id] = {"password": password, "expires_at": expiry_time}

        await message.reply_text(
            f"✅ <b>Temporary Password:</b> <code>{password}</code>\n"
            f"Expires in: <b>{format_time(time_in_minutes)}</b>",
            parse_mode="html",
        )
    except ValueError:
        await message.reply_text("❌ <b>Invalid user_id or time format!</b>", parse_mode="html")

# /unauth command (Owner only)
@app.on_message(filters.command("unauth") & filters.user(OWNER_ID))
async def unauth(client, message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply_text("❌ <b>Invalid Usage!</b> Use: <code>/unauth user_id</code>", parse_mode="html")
        return

    user_id = int(parts[1])
    users_collection.update_one({"user_id": user_id}, {"$set": {"authorized": False}})
    await message.reply_text(f"✅ <b>User {user_id} unauthorized!</b>", parse_mode="html")

# /stats command (Owner only)
@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message: Message):
    authorized_count = users_collection.count_documents({"authorized": True})
    uptime = datetime.now() - BOT_START_TIME

    await message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Authorized Users: <b>{authorized_count}</b>\n"
        f"⏱ Uptime: <b>{str(uptime).split('.')[0]}</b>",
        parse_mode="html",
    )

# /users command (Owner only)
@app.on_message(filters.command("users") & filters.user(OWNER_ID))
async def users(client, message: Message):
    users = users_collection.find({"authorized": True})
    user_list = "\n".join(
        [f"👤 @{user.get('username', 'Unknown')} (<code>{user['user_id']}</code>)" for user in users]
    )

    if not user_list:
        user_list = "No authorized users."

    await message.reply_text(
        f"👥 <b>Authorized Users:</b>\n\n{user_list}",
        parse_mode="html",
    )

# /msg command (Owner only)
@app.on_message(filters.command("msg") & filters.user(OWNER_ID))
async def msg(client, message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("❌ <b>Invalid Usage!</b> Use: <code>/msg user_id message</code>", parse_mode="html")
        return

    target_id = int(parts[1])
    msg_text = " ".join(parts[2:])

    try:
        await client.send_message(target_id, msg_text)
        await message.reply_text("✅ <b>Message sent successfully!</b>", parse_mode="html")
    except Exception as e:
        await message.reply_text(f"❌ <b>Error:</b> {str(e)}", parse_mode="html")

# /req command (for authorized users)
@app.on_message(filters.command("req"))
async def req(client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await unauthorized_message(client, message)
        return

    request_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not request_text:
        await message.reply_text("❌ <b>Invalid Usage!</b> Use: <code>/req your_request</code>", parse_mode="html")
        return

    requests_collection.insert_one({"user_id": user_id, "request": request_text, "timestamp": datetime.now()})
    await message.reply_text("✅ <b>Your request has been submitted!</b>", parse_mode="html")

bot_loop = app.loop
app.loop.run_forever()
