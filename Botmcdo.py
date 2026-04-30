import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

# ================= DB =================
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        produit TEXT,
        prix REAL,
        statut TEXT DEFAULT 'en_attente'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT,
        resultat TEXT,
        type TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        prono_id INTEGER,
        vote TEXT
    )
    """)

    conn.commit()
    conn.close()

# ================= MENUS =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽️ Pronostics", callback_data="menu_prono")]
    ])

def prono_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽️ Prono du jour", callback_data="menu_prono_prono")],
        [InlineKeyboardButton("🎟 Ticket du jour", callback_data="menu_prono_ticket")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔥 Bot prêt"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ================= BUTTONS =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # ===== MENU PRONO =====
    if data == "menu_prono":
        await query.edit_message_text(
            "⚽️ Choisis :",
            reply_markup=prono_menu()
        )
        return

    # ===== PRONO DU JOUR =====
    if data == "menu_prono_prono":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT id, texte FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        prono_id = 0
        texte = "Aucun prono"

        if row:
            prono_id, texte = row

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='yes'", (prono_id,))
        yes = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='no'", (prono_id,))
        no = c.fetchone()[0]

        conn.close()

        await query.edit_message_text(
            f"⚽️ PRONO DU JOUR\n\n{texte}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"👍 {yes}", callback_data=f"vote_yes_{prono_id}"),
                    InlineKeyboardButton(f"👎 {no}", callback_data=f"vote_no_{prono_id}")
                ],
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
            ])
        )
        return

    # ===== TICKET =====
    if data == "menu_prono_ticket":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        texte = "Aucun ticket"

        if row:
            texte = row[0]

        conn.close()

        await query.edit_message_text(
            f"🎟 TICKET DU JOUR\n\n{texte}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
            ])
        )
        return

    # ===== BACK =====
    if data == "back":
        await start(update, context)
        return

    # ===== VOTES FIX SAFE =====
    if data.startswith("vote_"):
        parts = data.split("_")

        if len(parts) != 3:
            return

        _, vote, prono_id = parts
        prono_id = int(prono_id)

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("DELETE FROM votes WHERE user_id=? AND prono_id=?", (user.id, prono_id))
        c.execute("INSERT INTO votes (user_id, prono_id, vote) VALUES (?,?,?)",
                  (user.id, prono_id, vote))

        conn.commit()
        conn.close()

        await query.answer("Vote OK")
        return

# ================= ADMIN =================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?,?,?)",
              (texte, "attente", "prono"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Prono ajouté")

async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?,?,?)",
              (texte, "attente", "ticket"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Ticket ajouté")

# ================= MAIN =================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))

    print("🚀 BOT OK FIXED")
    app.run_polling()
