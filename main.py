import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

# =========================
# 🔧 CONFIG
# =========================
BOT_TOKEN = "6917908247:AAFaCE0R3yfd4GCwTPIoyKLczilRzXapGCI"
MONGO_URI = "mongodb+srv://rahulmardhandaa143_db_user:HdLCMeFOFKlMjXMQ@cluster0.hssdcsh.mongodb.net/"
REPORT_CHANNEL_ID = -1003077576672  # replace with your channel id
CHANNEL_TO_JOIN = -1003080703906  # replace with your channel id

SYSTEM_DBS = {"admin", "local", "config", "_quiz_meta_"}

# =========================
# 🔌 Logging
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quiz-bot")

# =========================
# 🌐 MongoDB
# =========================
client = MongoClient(MONGO_URI)
meta_db = client["_quiz_meta_"]
user_progress_col = meta_db["user_progress"]
user_results_col = meta_db["user_results"]

logger.info("✅ MongoDB connected successfully")

# =========================
# 🧠 Helpers
# =========================
def list_user_dbs() -> List[str]:
    return [dbname for dbname in client.list_database_names() if dbname not in SYSTEM_DBS]

def list_collections(dbname: str) -> List[str]:
    return client[dbname].list_collection_names()

def clean_question_text(text: str) -> str:
    return re.sub(r"^\s*\d+\.\s*", "", text or "").strip()

def fetch_nonrepeating_questions(dbname: str, colname: Optional[str], user_id: int, n: int = 10) -> List[Dict[str, Any]]:
    prog_key = {"user_id": user_id, "db": dbname, "collection": colname or "_RANDOM_"}
    doc = user_progress_col.find_one(prog_key) or {}
    served = set(doc.get("served_qids", []))
    results = []

    if colname:
        pool = list(client[dbname][colname].aggregate([
            {"$match": {"question_id": {"$nin": list(served)}}},
            {"$sample": {"size": n * 5}}
        ]))
    else:
        cols = list_collections(dbname)
        pool = []
        for cname in cols:
            pool += list(client[dbname][cname].aggregate([
                {"$match": {"question_id": {"$nin": list(served)}}},
                {"$sample": {"size": max(3, n)}}
            ]))

    random.shuffle(pool)
    for q in pool:
        if q.get("question_id") not in served:
            results.append(q)
            served.add(q.get("question_id"))
        if len(results) >= n:
            break

    user_progress_col.update_one(prog_key, {"$set": {"served_qids": list(served)}}, upsert=True)
    return results[:n]

def format_question_card(q: Dict[str, Any]) -> str:
    qtext = clean_question_text(q.get("question", ""))
    opts = [
        f"(A) {q.get('option_a','')}",
        f"(B) {q.get('option_b','')}",
        f"(C) {q.get('option_c','')}",
        f"(D) {q.get('option_d','')}",
    ]
    return f"{qtext}\n\n" + "\n".join(opts)

def build_option_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(l, callback_data=f"ans:{l.lower()}")] for l in ["A","B","C","D"]]
    return InlineKeyboardMarkup(buttons)

def motivational_message() -> str:
    msgs = [
        "Great job! Keep going 💪",
        "Nice! Every attempt makes you sharper 🚀",
        "Well done! 🔥",
        "Progress over perfection ✅",
    ]
    return random.choice(msgs)

# =========================
# 🧩 Handlers
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    db_names = list_user_dbs()
    keyboard = [[InlineKeyboardButton(db, callback_data=f"db:{db}")] for db in db_names]
    await context.bot.send_message(chat_id, "👋 Welcome! Select a subject:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("db:"):
        dbname = data.split(":", 1)[1]
        cols = list_collections(dbname)
        buttons = [[InlineKeyboardButton("🎲 Random", callback_data=f"rnd:{dbname}")]]
        for cname in cols:
            buttons.append([InlineKeyboardButton(cname, callback_data=f"col:{dbname}:{cname}")])
        await query.edit_message_text(f"📚 {dbname} selected. Choose a topic:", reply_markup=InlineKeyboardMarkup(buttons))

async def send_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = context.user_data["session"]
    q = session["questions"][session["i"]]
    await context.bot.send_message(chat_id, format_question_card(q), reply_markup=build_option_keyboard())

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
