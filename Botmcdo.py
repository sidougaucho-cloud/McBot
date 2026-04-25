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
    {"nom": "Cagnotte 100-124 pts
