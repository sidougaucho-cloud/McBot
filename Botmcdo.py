import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

# ==================== BASE DE DONNÉES ====================
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
    c.execute("""INSERT INTO commandes 
                 (user_id, username, produit, prix) 
                 VALUES (?, ?, ?, ?)""", 
              (user_id, username, produit, prix))
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return cid

# ==================== PRODUITS ====================
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

# ==================== MENU PRINCIPAL ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🍔 McDo Cagnottes",
