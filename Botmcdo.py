import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ================= SAFE CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# FIX IMPORTANT (évite crash Railway)
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)

PAYPAL_EMAIL = "Sidou.gaucho@gmail.com"

logging.basicConfig(level=logging.INFO)

# STOP SI TOKEN MANQUANT
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN manquant dans Railway")

# ================= PRODUITS =================
PRODUITS = {
    "mcdo": [
        ("Cagnotte 50-74 pts", 2.0), ("Cagnotte 75-99 pts", 3.5),
        ("Cagnotte 100-124 pts", 4.5), ("Cagnotte 125-174 pts", 6.5),
        ("Cagnotte 175-199 pts", 8.0), ("Cagnotte 200-249 pts", 9.5),
        ("Cagnotte 250-299 pts", 10.5), ("Cagnotte 300-324 pts", 11.5),
        ("Cagnotte 325-374 pts", 12.0), ("Cagnotte 375-400 pts", 13.0),
        ("Cagnotte 400-499 pts", 14.0), ("Cagnotte 500-599 pts", 19.0),
    ],
    "abo": [("Netflix", 5.0), ("Deezer Premium", 5.0)],
    "snap": [("Tech Snapchat +", 25.0), ("Tech erreur SS06", 20.0)],
    "tech": [("Tech Uber Eat", 20.0)]
}

# ================= DB =================
def init_db():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, produit TEXT,
        prix REAL, statut TEXT DEFAULT 'en_attente'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT, resultat TEXT, type TEXT
    )""")

    conn.commit()
    conn.close()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🔥🚨 Bienvenue sur le shop !

🛍️ Choisis ton article puis paie via PayPal
🆘 SAV : @Zeerkay"""
    await update.message.reply_text(text)

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abos", callback_data="menu_abo")],
        [InlineKeyboardButton("👻 Snap", callback_data="menu_snap")],
        [InlineKeyboardButton("📱 Tech", callback_data="menu_tech")],
        [InlineKeyboardButton("⚽ Pronos", callback_data="menu_prono")]
    ])

# ================= BUTTONS =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # sécurité proof (évite bug)
    if data.startswith("proof_"):
        await query.edit_message_text("📸 Preuve envoyée")
        return

    if data == "menu_prono":
        await query.edit_message_text("⚽ Pronostics")
        return

    if data.startswith("menu_"):
        cat = data.split("_")[1]
        produits = PRODUITS.get(cat, [])

        kb = [
            [InlineKeyboardButton(f"{p} - {x}€", callback_data=f"buy_{cat}_{i}")]
            for i, (p, x) in enumerate(produits)
        ]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])

        await query.edit_message_text("📦 Produits", reply_markup=InlineKeyboardMarkup(kb))

    if data == "back":
        await start(update, context)

# ================= PRONO =================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM pronos WHERE type='prono'")
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, 'attente', 'prono')", (texte,))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Prono mis à jour")

# ================= TICKET =================
async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM pronos WHERE type='ticket'")
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, '', 'ticket')", (texte,))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Ticket mis à jour")

# ================= MAIN =================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))

    print("🚀 Bot démarré")
    app.run_polling()
