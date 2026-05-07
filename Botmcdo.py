import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "8631179355:AAFdcqMSkeBtALMhpNWhlW8ocMn0OLv9-Ys"
ADMIN_ID = int(os.environ.get("ADMIN_ID") or 0)

logging.basicConfig(level=logging.INFO)

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
    "tech": [("Tech Uber Eat", 20.0)],
    "vip": [("Abonnement VIP - 30 jours", 9.99)]
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
    c.execute("""CREATE TABLE IF NOT EXISTS vip (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        expiry_date TEXT
    )""")
    conn.commit()
    conn.close()

# ================= MENUS =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")],
        [InlineKeyboardButton("👻 Snapchat", callback_data="menu_snap")],
        [InlineKeyboardButton("📱 Tech", callback_data="menu_tech")],
        [InlineKeyboardButton("⭐ VIP - Pronos", callback_data="menu_vip")],
        [InlineKeyboardButton("⚽️ Pronostics", callback_data="menu_prono")]
    ])

def prono_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽️ Prono du jour", callback_data="menu_prono_prono")],
        [InlineKeyboardButton("🎟 Ticket du jour", callback_data="menu_prono_ticket")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
    ])

def is_vip(user_id: int) -> bool:
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM vip WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    return datetime.fromisoformat(row[0]) > datetime.now()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🔥🚨 Bienvenu sur le shop ! 

✅  Boutique ouverte ! 

🛍️🛒 Pour commander rien de plus simple : 
Choisis l’article désiré ensuite effectue le paiement via PayPal. L’interface a été pensée simple pour plus de fluidité 

🆘 SAV : @keyzer135"""

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ================= BUTTON HANDLER (simplifié) =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ... (Tes menus et achats restent les mêmes)
    if data.startswith("proof_"):
        await query.edit_message_text("✅ Preuve envoyée à l'admin. En attente de validation.")
        return

    # Ajoute ici tes autres handlers (menu_, buy_, etc.)

# ================= ADDVIP CORRIGÉ =================
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Tu n'es pas autorisé à utiliser cette commande.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage :\n/addvip <user_id>\nExemple : /addvip 123456789")
        return

    try:
        target_id = int(context.args[0])
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO vip (user_id, username, expiry_date) 
                     VALUES (?, ?, ?)""", (target_id, "Manual", expiry_date))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ VIP ajouté avec succès pour l'ID {target_id}\nValable jusqu'au {expiry_date[:10]}")

        # Notification à l'utilisateur
        try:
            await context.bot.send_message(
                target_id,
                "🎉 Félicitations !\n\nTon abonnement **VIP** a été activé manuellement pour 30 jours.\nTu as maintenant accès au Prono du jour."
            )
        except:
            await update.message.reply_text("⚠️ Impossible d'envoyer le message à l'utilisateur (il a peut-être bloqué le bot).")

    except ValueError:
        await update.message.reply_text("❌ Erreur : L'ID doit être un nombre.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur inattendue : {e}")


# ================= MAIN =================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("setprono", set_prono))   # Ajoute tes autres commandes ici
    app.add_handler(CommandHandler("setticket", set_ticket))
    app.add_handler(CommandHandler("addvip", add_vip))

    print("🚀 Bot démarré - /addvip corrigé")
    app.run_polling()
