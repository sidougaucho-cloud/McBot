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
PAYPAL_EMAIL = "Sidou.gaucho@gmail.com"

logging.basicConfig(level=logging.INFO)

# ================= PRODUITS =================
PRODUITS = {
    "mcdo": [ ... ],  # Garde tes produits McDo
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

# ================= MENUS & VIP CHECK =================
def main_menu():
    return InlineKeyboardMarkup([ ... ])  # Garde ton menu

def prono_menu():
    return InlineKeyboardMarkup([ ... ])  # Garde ton menu

def is_vip(user_id: int) -> bool:
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM vip WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row: return False
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

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    username = query.from_user.username or "Inconnu"

    # ... (garde tout ton code menu_prono, buy_, etc. tel quel)

    if data.startswith("proof_"):
        _, cat, idx = data.split("_")
        idx = int(idx)
        produit, prix = PRODUITS[cat][idx]

        # Enregistrer la commande en attente
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("""INSERT INTO commandes (user_id, username, produit, prix, statut)
                     VALUES (?, ?, ?, ?, 'en_attente')""", 
                  (user_id, username, produit, prix))
        order_id = c.lastrowid
        conn.commit()
        conn.close()

        await query.edit_message_text("✅ Preuve envoyée. En attente de validation par l'admin.")

        # Notification à l'admin avec boutons
        keyboard = [
            [InlineKeyboardButton("✅ Valider VIP", callback_data=f"validate_vip_{user_id}_{order_id}")],
            [InlineKeyboardButton("❌ Refuser", callback_data=f"reject_{order_id}")]
        ]
        await context.bot.send_message(
            ADMIN_ID,
            f"🛒 **Nouvelle commande en attente**\n\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"📦 {produit}\n"
            f"💰 {prix}€\n"
            f"🆔 Order ID: {order_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ================= VALIDATION ADMIN =================
    if data.startswith("validate_vip_"):
        _, _, target_id, order_id = data.split("_")
        target_id = int(target_id)

        expiry = (datetime.now() + timedelta(days=30)).isoformat()

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO vip (user_id, username, expiry_date) VALUES (?, ?, ?)",
                  (target_id, username, expiry))
        c.execute("UPDATE commandes SET statut = 'validé' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()

        await query.edit_message_text("✅ Commande validée ! VIP activé pour 30 jours.")

        try:
            await context.bot.send_message(target_id, "🎉 Félicitations !\nTon abonnement **VIP** a été activé pour 30 jours.\nTu as maintenant accès au Prono du jour.")
        except:
            pass
        return

    if data.startswith("reject_"):
        order_id = int(data.split("_")[1])
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("UPDATE commandes SET statut = 'refusé' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text("❌ Commande refusée.")
        return

    # ... (le reste de ton button_handler : menu_, buy_, etc.)

# ================= COMMANDES ADMIN (Backup) =================
async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Accès refusé.")
        return
    # ... (code addvip existant)

# ================= MAIN =================
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))
    app.add_handler(CommandHandler("addvip", add_vip))

    print("🚀 Bot démarré avec validation manuelle VIP")
    app.run_polling()
