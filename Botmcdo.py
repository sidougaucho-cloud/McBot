import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

# Base de données
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

def save_commande(user_id, username, produit, prix):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?, ?, ?, ?)",
              (user_id, username, produit, prix))
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return cid

# Liste des produits
PRODUITS_MCDO = [
    {"nom": "Cagnotte 50-74 pts", "prix": 2.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 75-99 pts", "prix": 3.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 100-124 pts", "prix": 4.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 125-174 pts", "prix": 6.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 175-199 pts", "prix": 8.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 200-249 pts", "prix": 9.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 250-299 pts", "prix": 10.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 300-324 pts", "prix": 11.50, "categorie": "mcdo"},
    {"nom": "Cagnotte 325-374 pts", "prix": 12.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 375-400 pts", "prix": 13.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 400-499 pts", "prix": 14.00, "categorie": "mcdo"},
    {"nom": "Cagnotte 500-599 pts", "prix": 19.00, "categorie": "mcdo"},
]

PRODUITS_ABO = [
    {"nom": "Deezer Premium", "prix": 5.00, "categorie": "abo"},
    {"nom": "Netflix", "prix": 5.00, "categorie": "abo"},
]

# Menu principal
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Salut ! Bienvenue sur **McBot**\n\nQue veux-tu faire aujourd'hui ?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Gestion des boutons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "menu_mcdo":
        kb = [[InlineKeyboardButton(f"{p['nom']} - {p['prix']}€", callback_data=f"buy_{p['categorie']}_{p['nom']}")] for p in PRODUITS_MCDO]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])
        await query.edit_message_text("🍔 **Cagnottes McDo disponibles :**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data == "menu_abo":
        kb = [[InlineKeyboardButton(f"{p['nom']} - {p['prix']}€", callback_data=f"buy_{p['categorie']}_{p['nom']}")] for p in PRODUITS_ABO]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])
        await query.edit_message_text("📺 **
