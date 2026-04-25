import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
ApplicationBuilder, CommandHandler, CallbackQueryHandler,
MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = os.environ.get(“BOT_TOKEN”)
ADMIN_ID = int(os.environ.get(“ADMIN_ID”, “0”))
PAYPAL_EMAIL = os.environ.get(“PAYPAL_EMAIL”, “”)

PRODUITS_MCDO = [
{“nom”: “Cagnotte 50-74 pts”,   “points”: “50-74 pts”,   “prix”: 2.00,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 75-99 pts”,   “points”: “75-99 pts”,   “prix”: 3.50,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 100-124 pts”, “points”: “100-124 pts”, “prix”: 4.50,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 125-174 pts”, “points”: “125-174 pts”, “prix”: 6.50,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 175-199 pts”, “points”: “175-199 pts”, “prix”: 8.00,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 200-249 pts”, “points”: “200-249 pts”, “prix”: 9.50,  “categorie”: “mcdo”},
{“nom”: “Cagnotte 250-299 pts”, “points”: “250-299 pts”, “prix”: 10.50, “categorie”: “mcdo”},
{“nom”: “Cagnotte 300-324 pts”, “points”: “300-324 pts”, “prix”: 11.50, “categorie”: “mcdo”},
{“nom”: “Cagnotte 325-374 pts”, “points”: “325-374 pts”, “prix”: 12.00, “categorie”: “mcdo”},
{“nom”: “Cagnotte 375-400 pts”, “points”: “375-400 pts”, “prix”: 13.00, “categorie”: “mcdo”},
{“nom”: “Cagnotte 400-499 pts”, “points”: “400-499 pts”, “prix”: 14.00, “categorie”: “mcdo”},
{“nom”: “Cagnotte 500-599 pts”, “points”: “500-599 pts”, “prix”: 19.00, “categorie”: “mcdo”},
]

PRODUITS_ABONNEMENTS = [
{“nom”: “Deezer Premium”, “description”: “1 mois Deezer Premium”, “prix”: 5.00, “categorie”: “abo”},
{“nom”: “Netflix”,        “description”: “1 mois Netflix”,        “prix”: 5.00, “categorie”: “abo”},
]

PRODUITS = PRODUITS_MCDO + PRODUITS_ABONNEMENTS
ATTENTE_PREUVE = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

def init_db():
conn = sqlite3.connect(“bot.db”)
c = conn.cursor()
c.execute(”””
CREATE TABLE IF NOT EXISTS commandes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
username TEXT,
produit TEXT,
prix REAL,
statut TEXT DEFAULT ‘en_attente’,
date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
“””)
conn.commit()
conn.close()

def save_commande(user_id, username, produit, prix):
conn = sqlite3.connect(“bot.db”)
c = conn.cursor()
c.execute(
“INSERT INTO commandes (user_id, username, produit, prix) VALUES (?, ?, ?, ?)”,
(user_id, username, produit, prix)
)
cid = c.lastrowid
conn.commit()
conn.close()
return cid

def get_commandes(user_id):
conn = sqlite3.connect(“bot.db”)
c = conn.cursor()
c.execute(
“SELECT id, produit, prix, statut, date FROM commandes WHERE user_id=? ORDER BY date DESC LIMIT 10”,
(user_id,)
)
rows = c.fetchall()
conn.close()
return rows

def update_statut(cid, statut):
conn = sqlite3.connect(“bot.db”)
c = conn.cursor()
c.execute(“UPDATE commandes SET statut=? WHERE id=?”, (statut, cid))
conn.commit()
conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
kb = [
[InlineKeyboardButton(“Boutique”, callback_data=“boutique”)],
[InlineKeyboardButton(“Mes commandes”, callback_data=“mes_commandes”)],
]
await update.message.reply_text(
f”Bienvenue sur McDo Bot!\n\n”
f”Utilisateur: @{user.username or user.first_name}\n”
f”ID: {user.id}\n\n”
f”Boutique ouverte\n\n”
f”Support: @zeerkay\n\n”
f”Clique sur les boutons ci-dessous:”,
reply_markup=InlineKeyboardMarkup(kb)
)

async def boutique(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
kb = [
[InlineKeyboardButton(“Cagnottes McDonald’s”, callback_data=“cat_mcdo”)],
[InlineKeyboardButton(“Abonnements”,          callback_data=“cat_abo”)],
[InlineKeyboardButton(“Retour”,               callback_data=“menu”)],
]
await query.edit_message_text(“Boutique\n\nChoisis une categorie:”, reply_markup=InlineKeyboardMarkup(kb))

async def cat_mcdo(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
kb = []
for i, p in enumerate(PRODUITS_MCDO):
kb.append([InlineKeyboardButton(f”{p[‘nom’]} - {p[‘prix’]}EUR”, callback_data=f”produit_{i}”)])
kb.append([InlineKeyboardButton(“Retour”, callback_data=“boutique”)])
await query.edit_message_text(“Cagnottes McDonald’s\n\nSelectionne:”, reply_markup=InlineKeyboardMarkup(kb))

async def cat_abo(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
kb = []
offset = len(PRODUITS_MCDO)
for i, p in enumerate(PRODUITS_ABONNEMENTS):
kb.append([InlineKeyboardButton(f”{p[‘nom’]} - {p[‘prix’]}EUR”, callback_data=f”produit_{offset+i}”)])
kb.append([InlineKeyboardButton(“Retour”, callback_data=“boutique”)])
await query.edit_message_text(“Abonnements\n\nSelectionne:”, reply_markup=InlineKeyboardMarkup(kb))

async def detail_produit(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
index = int(query.data.split(”*”)[1])
p = PRODUITS[index]
context.user_data[“produit”] = p
retour = “cat_mcdo” if p[“categorie”] == “mcdo” else “cat_abo”
kb = [
[InlineKeyboardButton(“Commander”, callback_data=f”commander*{index}”)],
[InlineKeyboardButton(“Retour”, callback_data=retour)],
]
if p[“categorie”] == “mcdo”:
texte = f”{p[‘nom’]}\nPoints: {p[‘points’]}\nPrix: {p[‘prix’]}EUR\n\nPaiement PayPal uniquement.”
else:
texte = f”{p[‘nom’]}\n{p[‘description’]}\nPrix: {p[‘prix’]}EUR\n\nPaiement PayPal uniquement.”
await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(kb))

async def commander(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
index = int(query.data.split(”_”)[1])
p = PRODUITS[index]
context.user_data[“produit”] = p
await query.edit_message_text(
f”Paiement PayPal\n\n”
f”Produit: {p[‘nom’]}\n”
f”Montant: {p[‘prix’]}EUR\n\n”
f”Envoie {p[‘prix’]}EUR en Famille et amis a:\n”
f”{PAYPAL_EMAIL}\n\n”
f”Note: ton @username Telegram\n\n”
f”Envoie-moi la capture d’ecran du paiement.”
)
return ATTENTE_PREUVE

async def recevoir_preuve(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
p = context.user_data.get(“produit”)
if not p:
await update.message.reply_text(“Erreur. Tape /start pour recommencer.”)
return ConversationHandler.END

```
cid = save_commande(user.id, user.username or user.first_name, p["nom"], p["prix"])
caption = (
    f"Nouvelle commande #{cid}\n\n"
    f"Client: @{user.username or user.first_name} ({user.id})\n"
    f"Produit: {p['nom']}\n"
    f"Prix: {p['prix']}EUR"
)
kb_admin = [[
    InlineKeyboardButton("Valider", callback_data=f"valider_{cid}_{user.id}"),
    InlineKeyboardButton("Refuser", callback_data=f"refuser_{cid}_{user.id}")
]]
try:
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(kb_admin)
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=caption,
            reply_markup=InlineKeyboardMarkup(kb_admin)
        )
except Exception as e:
    logger.error(f"Erreur admin: {e}")

await update.message.reply_text(
    f"Commande #{cid} recue!\n\nVerification en cours.\nSupport: @zeerkay"
)
return ConversationHandler.END
```

async def valider(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
if query.from_user.id != ADMIN_ID:
await query.answer(“Non autorise”, show_alert=True)
return
await query.answer()
parts = query.data.split(”_”)
cid, client_id = int(parts[1]), int(parts[2])
update_statut(cid, “validee”)
await context.bot.send_message(
chat_id=client_id,
text=f”Commande #{cid} validee!\nTa commande arrive bientot.\nSupport: @zeerkay”
)
await query.edit_message_caption(caption=(query.message.caption or “”) + “\n\nVALIDEE”)

async def refuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
if query.from_user.id != ADMIN_ID:
await query.answer(“Non autorise”, show_alert=True)
return
await query.answer()
parts = query.data.split(”_”)
cid, client_id = int(parts[1]), int(parts[2])
update_statut(cid, “refusee”)
await context.bot.send_message(
chat_id=client_id,
text=f”Commande #{cid} refusee.\nContacte le support.\nSupport: @zeerkay”
)
await query.edit_message_caption(caption=(query.message.caption or “”) + “\n\nREFUSEE”)

async def mes_commandes(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
commandes = get_commandes(query.from_user.id)
if not commandes:
texte = “Mes commandes\n\nAucune commande pour l’instant.”
else:
texte = “Mes commandes\n\n”
for cmd in commandes:
texte += f”#{cmd[0]} - {cmd[1]} - {cmd[2]}EUR - {cmd[3]}\n”
kb = [[InlineKeyboardButton(“Retour”, callback_data=“menu”)]]
await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(kb))

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = query.from_user
kb = [
[InlineKeyboardButton(“Boutique”, callback_data=“boutique”)],
[InlineKeyboardButton(“Mes commandes”, callback_data=“mes_commandes”)],
]
await query.edit_message_text(
f”Bienvenue sur McDo Bot!\n\n”
f”Utilisateur: @{user.username or user.first_name}\n\n”
f”Support: @zeerkay”,
reply_markup=InlineKeyboardMarkup(kb)
)

async def annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(“Annule. Tape /start.”)
return ConversationHandler.END

def main():
init_db()
app = ApplicationBuilder().token(BOT_TOKEN).build()

```
conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(commander, pattern="^commander_")],
    states={ATTENTE_PREUVE: [MessageHandler(filters.PHOTO | filters.TEXT, recevoir_preuve)]},
    fallbacks=[CommandHandler("annuler", annuler)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(boutique,       pattern="^boutique$"))
app.add_handler(CallbackQueryHandler(cat_mcdo,       pattern="^cat_mcdo$"))
app.add_handler(CallbackQueryHandler(cat_abo,        pattern="^cat_abo$"))
app.add_handler(CallbackQueryHandler(detail_produit, pattern="^produit_"))
app.add_handler(CallbackQueryHandler(mes_commandes,  pattern="^mes_commandes$"))
app.add_handler(CallbackQueryHandler(menu,           pattern="^menu$"))
app.add_handler(CallbackQueryHandler(valider,        pattern="^valider_"))
app.add_handler(CallbackQueryHandler(refuser,        pattern="^refuser_"))

logger.info("Bot demarre!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
