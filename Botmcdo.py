import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8643176773:AAFfN7IUIXWV6rpyknTk3LfTcsYXoK51tDU"
ADMIN_ID = @zeerkay  # Mets ton ID Telegram ici (cherche @userinfobot)
PAYPAL_EMAIL = "Kakuta13500@gmail.com"  # Mets ton PayPal ici

# ==================== PRODUITS ====================
PRODUITS_MCDO = [
    {"nom": "🍔 Cagnotte 50-74 pts",   "points": "50-74 pts",   "prix": 2.00,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 75-99 pts",   "points": "75-99 pts",   "prix": 3.50,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 100-124 pts", "points": "100-124 pts", "prix": 4.50,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 125-174 pts", "points": "125-174 pts", "prix": 6.50,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 175-199 pts", "points": "175-199 pts", "prix": 8.00,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 200-249 pts", "points": "200-249 pts", "prix": 9.50,  "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 250-299 pts", "points": "250-299 pts", "prix": 10.50, "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 300-324 pts", "points": "300-324 pts", "prix": 11.50, "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 325-374 pts", "points": "325-374 pts", "prix": 12.00, "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 375-400 pts", "points": "375-400 pts", "prix": 13.00, "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 400-499 pts", "points": "400-499 pts", "prix": 14.00, "categorie": "mcdo"},
    {"nom": "🍔 Cagnotte 500-599 pts", "points": "500-599 pts", "prix": 19.00, "categorie": "mcdo"},
]

PRODUITS_ABONNEMENTS = [
    {"nom": "🟢 Deezer Premium", "description": "1 mois Deezer Premium", "prix": 5.00, "categorie": "abo"},
    {"nom": "🔴 Netflix",        "description": "1 mois Netflix",        "prix": 5.00, "categorie": "abo"},
]

# Liste combinée pour accès par index global
PRODUITS = PRODUITS_MCDO + PRODUITS_ABONNEMENTS

# ==================== ÉTATS CONVERSATION ====================
ATTENTE_PREUVE_PAIEMENT = 1
ATTENTE_ADRESSE_LIVRAISON = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== BASE DE DONNÉES ====================
def init_db():
    conn = sqlite3.connect("mcdo_bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS commandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            produit TEXT,
            prix REAL,
            statut TEXT DEFAULT 'en_attente',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def sauvegarder_commande(user_id, username, produit, prix):
    conn = sqlite3.connect("mcdo_bot.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO commandes (user_id, username, produit, prix) VALUES (?, ?, ?, ?)",
        (user_id, username, produit, prix)
    )
    commande_id = c.lastrowid
    conn.commit()
    conn.close()
    return commande_id

def get_commandes_user(user_id):
    conn = sqlite3.connect("mcdo_bot.db")
    c = conn.cursor()
    c.execute(
        "SELECT id, produit, prix, statut, date FROM commandes WHERE user_id = ? ORDER BY date DESC LIMIT 10",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def update_statut_commande(commande_id, statut):
    conn = sqlite3.connect("mcdo_bot.db")
    c = conn.cursor()
    c.execute("UPDATE commandes SET statut = ? WHERE id = ?", (statut, commande_id))
    conn.commit()
    conn.close()

# ==================== MENU PRINCIPAL ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🛒 Boutique", callback_data="boutique")],
        [InlineKeyboardButton("📋 Mes commandes", callback_data="mes_commandes")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    texte = (
        f"🔥 *Bienvenue sur McDo_Bot !*\n\n"
        f"👤 : @{user.username or user.first_name}\n"
        f"🆔 : `{user.id}`\n\n"
        f"🟢 Boutique ouverte\n\n"
        f"🛍️ Ici, tu peux commander simplement et rapidement.\n"
        f"Tout est pensé pour que ce soit propre, fluide et efficace.\n\n"
        f"🆘 Support : @zeerkay\n\n"
        f"👇 Clique sur les boutons ci-dessous :"
    )
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== BOUTIQUE — MENU CATÉGORIES ====================
async def boutique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🍔 Cagnottes McDonald's", callback_data="categorie_mcdo")],
        [InlineKeyboardButton("📺 Abonnements",          callback_data="categorie_abo")],
        [InlineKeyboardButton("🔙 Retour",               callback_data="retour_menu")],
    ]

    await query.edit_message_text(
        "🛒 *Boutique*\n\nChoisis une catégorie :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== CATÉGORIE MCDO ====================
async def categorie_mcdo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for i, produit in enumerate(PRODUITS_MCDO):
        keyboard.append([
            InlineKeyboardButton(
                f"{produit['nom']} — {produit['prix']}€",
                callback_data=f"produit_{i}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Retour boutique", callback_data="boutique")])

    await query.edit_message_text(
        "🍔 *Cagnottes McDonald's*\n\nSélectionne la cagnotte souhaitée :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== CATÉGORIE ABONNEMENTS ====================
async def categorie_abo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    offset = len(PRODUITS_MCDO)
    for i, produit in enumerate(PRODUITS_ABONNEMENTS):
        keyboard.append([
            InlineKeyboardButton(
                f"{produit['nom']} — {produit['prix']}€",
                callback_data=f"produit_{offset + i}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Retour boutique", callback_data="boutique")])

    await query.edit_message_text(
        "📺 *Abonnements*\n\nSélectionne l'abonnement souhaité :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== DÉTAIL PRODUIT ====================
async def detail_produit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data.split("_")[1])
    produit = PRODUITS[index]
    context.user_data["produit_selectionne"] = produit

    retour = "categorie_mcdo" if produit.get("categorie") == "mcdo" else "categorie_abo"

    keyboard = [
        [InlineKeyboardButton("✅ Commander", callback_data=f"commander_{index}")],
        [InlineKeyboardButton("🔙 Retour", callback_data=retour)],
    ]

    if produit.get("categorie") == "mcdo":
        texte = (
            f"🍔 *{produit['nom']}*\n\n"
            f"📊 Points : `{produit['points']}`\n"
            f"💰 Prix : *{produit['prix']}€*\n\n"
            f"💳 Paiement via PayPal uniquement."
        )
    else:
        texte = (
            f"📺 *{produit['nom']}*\n\n"
            f"📝 {produit['description']}\n"
            f"💰 Prix : *{produit['prix']}€*\n\n"
            f"💳 Paiement via PayPal uniquement."
        )
    await query.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== COMMANDER ====================
async def commander(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data.split("_")[1])
    produit = PRODUITS[index]
    context.user_data["produit_selectionne"] = produit

    texte = (
        f"💳 *Paiement PayPal*\n\n"
        f"Produit : *{produit['nom']}*\n"
        f"Montant : *{produit['prix']}€*\n\n"
        f"📩 Envoie *{produit['prix']}€* en paiement *Famille et amis* à :\n"
        f"`{PAYPAL_EMAIL}`\n\n"
        f"⚠️ *IMPORTANT* : Mets en note ton @username Telegram\n\n"
        f"📸 Une fois le paiement effectué, envoie-moi la *capture d'écran* de ta transaction."
    )
    await query.edit_message_text(texte, parse_mode="Markdown")
    return ATTENTE_PREUVE_PAIEMENT

# ==================== RÉCEPTION PREUVE PAIEMENT ====================
async def recevoir_preuve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    produit = context.user_data.get("produit_selectionne")

    if not produit:
        await update.message.reply_text("❌ Erreur. Recommence depuis /start")
        return ConversationHandler.END

    # Sauvegarder la commande
    commande_id = sauvegarder_commande(
        user.id,
        user.username or user.first_name,
        produit["nom"],
        produit["prix"]
    )

    # Notifier l'admin
    caption_admin = (
        f"🔔 *Nouvelle commande #{commande_id}*\n\n"
        f"👤 Client : @{user.username or user.first_name} (`{user.id}`)\n"
        f"🛒 Produit : {produit['nom']}\n"
        f"💰 Prix : {produit['prix']}€\n\n"
        f"📸 Preuve de paiement ci-dessous :"
    )

    keyboard_admin = [
        [
            InlineKeyboardButton("✅ Valider", callback_data=f"valider_{commande_id}_{user.id}"),
            InlineKeyboardButton("❌ Refuser", callback_data=f"refuser_{commande_id}_{user.id}")
        ]
    ]

    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption_admin,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard_admin)
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=update.message.document.file_id,
                caption=caption_admin,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard_admin)
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=caption_admin + "\n\n⚠️ Aucune image reçue.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard_admin)
            )
    except Exception as e:
        logger.error(f"Erreur envoi admin: {e}")

    await update.message.reply_text(
        f"✅ *Commande #{commande_id} reçue !*\n\n"
        f"Ton paiement est en cours de vérification.\n"
        f"Tu recevras ta cagnotte dès validation. 🍔\n\n"
        f"🆘 Support : @zeerkay",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ==================== ADMIN — VALIDER / REFUSER ====================
async def valider_commande(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Non autorisé", show_alert=True)
        return

    parts = query.data.split("_")
    commande_id = int(parts[1])
    client_id = int(parts[2])

    update_statut_commande(commande_id, "validée")

    await context.bot.send_message(
        chat_id=client_id,
        text=(
            f"✅ *Commande #{commande_id} validée !*\n\n"
            f"Ta cagnotte McDonald's va t'être envoyée très prochainement.\n"
            f"Merci pour ta confiance ! 🍔\n\n"
            f"🆘 Support : @zeerkay"
        ),
        parse_mode="Markdown"
    )
    await query.edit_message_caption(
        caption=query.message.caption + "\n\n✅ *VALIDÉE*",
        parse_mode="Markdown"
    )

async def refuser_commande(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Non autorisé", show_alert=True)
        return

    parts = query.data.split("_")
    commande_id = int(parts[1])
    client_id = int(parts[2])

    update_statut_commande(commande_id, "refusée")

    await context.bot.send_message(
        chat_id=client_id,
        text=(
            f"❌ *Commande #{commande_id} refusée*\n\n"
            f"Ton paiement n'a pas pu être vérifié.\n"
            f"Contacte le support pour plus d'infos.\n\n"
            f"🆘 Support : @zeerkay"
        ),
        parse_mode="Markdown"
    )
    await query.edit_message_caption(
        caption=query.message.caption + "\n\n❌ *REFUSÉE*",
        parse_mode="Markdown"
    )

# ==================== MES COMMANDES ====================
async def mes_commandes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    commandes = get_commandes_user(user_id)

    if not commandes:
        texte = "📋 *Mes commandes*\n\nTu n'as pas encore passé de commande."
    else:
        texte = "📋 *Mes commandes*\n\n"
        for cmd in commandes:
            statut_emoji = {"en_attente": "⏳", "validée": "✅", "refusée": "❌"}.get(cmd[3], "❓")
            texte += f"{statut_emoji} *#{cmd[0]}* — {cmd[1]} — {cmd[2]}€\n"
            texte += f"   └ Statut : {cmd[3]} | {cmd[4][:10]}\n\n"

    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="retour_menu")]]
    await query.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== RETOUR MENU ====================
async def retour_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    keyboard = [
        [InlineKeyboardButton("🛒 Boutique", callback_data="boutique")],
        [InlineKeyboardButton("📋 Mes commandes", callback_data="mes_commandes")],
    ]
    texte = (
        f"🔥 *Bienvenue sur McDo_Bot !*\n\n"
        f"👤 : @{user.username or user.first_name}\n"
        f"🆔 : `{user.id}`\n\n"
        f"🟢 Boutique ouverte\n\n"
        f"🛍️ Ici, tu peux commander simplement et rapidement.\n\n"
        f"🆘 Support : @zeerkay\n\n"
        f"👇 Clique sur les boutons ci-dessous :"
    )
    await query.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ANNULER ====================
async def annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Commande annulée. Tape /start pour recommencer.")
    return ConversationHandler.END

# ==================== MAIN ====================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(commander, pattern="^commander_")],
        states={
            ATTENTE_PREUVE_PAIEMENT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, recevoir_preuve)
            ],
        },
        fallbacks=[CommandHandler("annuler", annuler)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(boutique, pattern="^boutique$"))
    app.add_handler(CallbackQueryHandler(categorie_mcdo, pattern="^categorie_mcdo$"))
    app.add_handler(CallbackQueryHandler(categorie_abo, pattern="^categorie_abo$"))
    app.add_handler(CallbackQueryHandler(detail_produit, pattern="^produit_"))
    app.add_handler(CallbackQueryHandler(mes_commandes, pattern="^mes_commandes$"))
    app.add_handler(CallbackQueryHandler(retour_menu, pattern="^retour_menu$"))
    app.add_handler(CallbackQueryHandler(valider_commande, pattern="^valider_"))
    app.add_handler(CallbackQueryHandler(refuser_commande, pattern="^refuser_"))

    logger.info("✅ McDo_Bot démarré !")
    app.run_polling()

if __name__ == "__main__":
