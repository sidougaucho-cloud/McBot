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
    c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?, ?, ?, ?)",
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
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Salut ! Bienvenue sur **McBot**\n\nQue veux-tu faire aujourd'hui ?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ==================== GESTION BOUTONS ====================
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
        await query.edit_message_text("📺 **Abonnements disponibles :**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif query.data == "back_main":
        await start(update, context)

    elif query.data.startswith("buy_"):
        _, categorie, *nom_parts = query.data.split("_")
        nom = " ".join(nom_parts)
        produits = PRODUITS_MCDO if categorie == "mcdo" else PRODUITS_ABO
        prix = next((p["prix"] for p in produits if p["nom"] == nom), 0.0)

        cid = save_commande(user.id, user.username or user.first_name, nom, prix)

        context.user_data["current_command_id"] = cid
        context.user_data["current_product"] = nom

        await query.edit_message_text(
            f"✅ Commande #{cid} enregistrée !\n\n"
            f"Produit : **{nom}**\n"
            f"Prix : **{prix} €**\n\n"
            "Envoie maintenant une **preuve de paiement** (photo ou capture d'écran).",
            parse_mode="Markdown"
        )

# ==================== RÉCEPTION PREUVE PAIEMENT ====================
async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_command_id" not in context.user_data:
        await update.message.reply_text("❌ Aucune commande en cours. Tape /start pour recommencer.")
        return

    cid = context.user_data["current_command_id"]
    product = context.user_data.get("current_product", "Produit inconnu")

    try:
        if update.message.photo:
            await update.message.forward(ADMIN_ID)
            await context.bot.send_message(
                ADMIN_ID,
                f"🛒 **Nouvelle preuve de paiement**\n"
                f"Commande #{cid}\n"
                f"Utilisateur : @{update.effective_user.username or update.effective_user.first_name}\n"
                f"Produit : {product}"
            )
        else:
            await update.message.forward(ADMIN_ID)
            await context.bot.send_message(ADMIN_ID, f"🛒 Preuve reçue pour commande #{cid} - {product}")
    except Exception as e:
        logging.error(f"Erreur envoi admin: {e}")

    await update.message.reply_text("✅ Ta preuve a été envoyée à l'admin ! Il va vérifier et valider ta commande rapidement.")

    context.user_data.clear()

# ==================== LANCEMENT DU BOT ====================
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    print("✅ McBot est en ligne et opérationnel !")
    app.run_polling()
