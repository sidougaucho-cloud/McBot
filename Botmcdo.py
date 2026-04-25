import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    produit TEXT,
                    prix REAL,
                    statut TEXT DEFAULT 'en_attente',
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

# ====================== MENU PRINCIPAL ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Salut ! Bienvenue sur **McBot**\n\n"
        "Que veux-tu faire aujourd'hui ?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ====================== GESTION DES BOUTONS ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # enlève le "chargement" sur le bouton

    if query.data == "menu_mcdo":
        keyboard = []
        for p in PRODUITS_MCDO:
            keyboard.append([InlineKeyboardButton(
                f"{p['nom']} - {p['prix']}€", 
                callback_data=f"buy_{p['categorie']}_{p['nom']}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("🍔 **Cagnottes McDo disponibles :**", 
                                      reply_markup=reply_markup, 
                                      parse_mode="Markdown")

    elif query.data == "menu_abo":
        keyboard = []
        for p in PRODUITS_ABO:
            keyboard.append([InlineKeyboardButton(
                f"{p['nom']} - {p['prix']}€", 
                callback_data=f"buy_{p['categorie']}_{p['nom']}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("📺 **Abonnements disponibles :**", 
                                      reply_markup=reply_markup, 
                                      parse_mode="Markdown")

    elif query.data.startswith("buy_"):
        # Pour l'instant on affiche juste un message
        await query.edit_message_text(f"✅ Tu as choisi : {query.data}\n\n"
                                      "La fonctionnalité d'achat arrive bientôt !")

    elif query.data == "back_main":
        await start(update, context)  # Retour au menu principal

# ====================== LISTE DES PRODUITS ======================
PRODUITS_MCDO = [
    {"nom": "Cagnotte 50-74 pts", "points": "50-74 pts", "prix": 2.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 75-99 pts", "points": "75-99 pts", "prix": 3.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 100-124 pts", "points": "100-124 pts", "prix": 4.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 125-174 pts", "points": "125-174 pts", "prix": 6.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 175-199 pts", "points": "175-199 pts", "prix": 8.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 200-249 pts", "points": "200-249 pts", "prix": 9.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 250-299 pts", "points": "250-299 pts", "prix": 10.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 300-324 pts", "points": "300-324 pts", "prix": 11.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 325-374 pts", "points": "325-374 pts", "prix": 12.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 375-400 pts", "points": "375-400 pts", "prix": 13.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 400-499 pts", "points": "400-499 pts", "prix": 14.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 500-599 pts", "points": "500-599 pts", "prix": 19.00, "categorie": "mcdo"},
]

PRODUITS_ABO = [
    {"nom": "Deezer Premium", "description": "1 mois Deezer Premium", "prix": 5.00, "categorie": "abo"},
    {"nom": "Netflix", "description": "1 mois Netflix", "prix": 5.00, "categorie": "abo"},
]

# ====================== LANCEMENT ======================
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ McBot démarré avec succès !")
    app.run_polling()
