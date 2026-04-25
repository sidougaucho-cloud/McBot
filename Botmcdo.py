import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PAYPAL_EMAIL = os.environ.get("PAYPAL_EMAIL", "")

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

PRODUITS = PRODUITS_MCDO + PRODUITS_ABO
ATTENTE_PREUVE = 1
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, produit TEXT, prix REAL, statut TEXT DEFAULT 'en_attente', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def save_cmd(uid, uname, produit, prix):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?, ?, ?, ?)", (uid, uname, produit, prix))
    cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid

def get_cmds(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT id, produit, prix, statut FROM commandes WHERE user_id=? ORDER BY date DESC LIMIT 10", (uid,))
    rows = c.fetchall()
    conn.close()
    return rows

def set_statut(cid, s):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE commandes SET statut=? WHERE id=?", (s, cid))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    kb​​​​​​​​​​​​​​​​
