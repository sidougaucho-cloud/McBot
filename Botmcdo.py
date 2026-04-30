import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PAYPAL_EMAIL = os.environ.get("PAYPAL_EMAIL", "")

logging.basicConfig(level=logging.INFO)

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect("bot.db")
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT,
        resultat TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ✅ AJOUT VOTES
    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        prono_id INTEGER,
        vote TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_commande(user_id, username, produit, prix):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO commandes (user_id, username, produit, prix)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, produit, prix))
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return cid

def set_statut(cid, statut):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE commandes SET statut = ? WHERE id = ?", (statut, cid))
    conn.commit()
    conn.close()

# ==================== PRODUCTS ====================
PRODUITS = {
    "mcdo": [
        ("Cagnotte 50-74 pts", 2.0),
        ("Cagnotte 75-99 pts", 3.5),
        ("Cagnotte 100-124 pts", 4.5),
        ("Cagnotte 125-174 pts", 6.5),
        ("Cagnotte 175-199 pts", 8.0),
        ("Cagnotte 200-249 pts", 9.5),
        ("Cagnotte 250-299 pts", 10.5),
        ("Cagnotte 300-324 pts", 11.5),
        ("Cagnotte 325-374 pts", 12.0),
        ("Cagnotte 375-400 pts", 13.0),
        ("Cagnotte 400-499 pts", 14.0),
        ("Cagnotte 500-599 pts", 19.0),
    ],
    "abo": [
        ("Netflix", 5.0),
        ("Deezer Premium", 5.0),
    ],
    "snap": [
        ("Tech Snapchat +", 25.0),
        ("Tech erreur SS06", 20.0),
    ],
    "tech": [
        ("Tech Uber Eat", 20.0),
    ]
}

# ==================== MENUS ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")],
        [InlineKeyboardButton("👻 Snapchat", callback_data="menu_snap")],
        [InlineKeyboardButton("📱 Tech", callback_data="menu_tech")],
        [InlineKeyboardButton("⚽️ Pronostics", callback_data="menu_prono")]
    ])

def products_menu(categorie, page=0, per_page=5):
    produits = PRODUITS[categorie]
    start = page * per_page
    end = start + per_page
    slice_prod = produits[start:end]

    kb = []

    for i, (nom, prix) in enumerate(slice_prod, start=start):
        kb.append([
            InlineKeyboardButton(
                f"{nom} - {prix}€",
                callback_data=f"buy_{categorie}_{i}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{categorie}_{page-1}"))
    if end < len(produits):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{categorie}_{page+1}"))

    if nav:
        kb.append(nav)

    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])

    return InlineKeyboardMarkup(kb)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥🚨 Bienvenue sur le shop !\n\n"
        "✅ Boutique ouverte\n\n"
        "🛍️🛒 Pour commander rien de plus simple :\n"
        "Choisis l’article désiré ensuite effectue le paiement via PayPal !\n"
        "L’interface a été pensée simple pour que ce soit plus fluide.\n\n"
        "🆘 SAV : @Zeerkay"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("menu_"):
        cat = data.split("_")[1]

        # ✅ PRONO AVEC VOTES
        if cat == "prono":
            conn = sqlite3.connect("bot.db")
            c = conn.cursor()

            c.execute("SELECT id, texte FROM pronos ORDER BY id DESC LIMIT 1")
            row = c.fetchone()

            if not row:
                texte = "Aucun pronostic aujourd’hui."
                prono_id = 0
            else:
                prono_id, texte = row

            c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='yes'", (prono_id,))
            yes = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='no'", (prono_id,))
            no = c.fetchone()[0]

            conn.close()

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"👍 {yes}", callback_data=f"vote_yes_{prono_id}"),
                    InlineKeyboardButton(f"👎 {no}", callback_data=f"vote_no_{prono_id}")
                ],
                [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
            ])

            await query.edit_message_text(
                f"⚽️ Pronostic du jour :\n\n{texte}",
                reply_markup=keyboard
            )
            return

        total_pages = (len(PRODUITS[cat]) - 1) // 5 + 1

        await query.edit_message_text(
            f"📦 Produits {cat}\nPage 1/{total_pages}",
            reply_markup=products_menu(cat, page=0)
        )

    elif data.startswith("page_"):
        _, cat, page = data.split("_")
        page = int(page)

        total_pages = (len(PRODUITS[cat]) - 1) // 5 + 1

        await query.edit_message_text(
            f"📦 Produits {cat}\nPage {page+1}/{total_pages}",
            reply_markup=products_menu(cat, page=page)
        )

    elif data == "back":
        await start(update, context)

    elif data.startswith("buy_"):
        _, cat, index = data.split("_")
        index = int(index)

        nom, prix = PRODUITS[cat][index]

        cid = save_commande(
            user.id,
            user.username or user.first_name,
            nom,
            prix
        )

        context.user_data["cid"] = cid
        context.user_data["product"] = nom

        paypal_link = f"https://paypal.me/{PAYPAL_EMAIL.split('@')[0]}" if PAYPAL_EMAIL else "https://paypal.com"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Payer avec PayPal", url=paypal_link)],
            [InlineKeyboardButton("✅ J'ai payé - Envoyer preuve", callback_data=f"proof_{cid}")]
        ])

        await query.edit_message_text(
            f"✅ Commande #{cid}\n\nProduit : {nom}\nPrix : {prix}€\n\nEnvoie une preuve 📸",
            reply_markup=keyboard
        )

    elif data.startswith("proof_"):
        cid = int(data.split("_")[1])
        context.user_data["cid"] = cid
        await query.edit_message_text("📸 Envoie ta preuve de paiement")

    elif data.startswith("validate_"):
        if query.from_user.id != ADMIN_ID:
            return await query.answer("❌ Admin seulement", show_alert=True)

        cid = int(data.split("_")[1])
        set_statut(cid, "validé")
        await query.edit_message_text(f"✅ Commande #{cid} validée")

    # ✅ GESTION DES VOTES
    elif data.startswith("vote_"):
        _, vote_type, prono_id = data.split("_")
        prono_id = int(prono_id)

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("DELETE FROM votes WHERE user_id=? AND prono_id=?", (user.id, prono_id))

        c.execute(
            "INSERT INTO votes (user_id, prono_id, vote) VALUES (?, ?, ?)",
            (user.id, prono_id, vote_type)
        )

        conn.commit()

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='yes'", (prono_id,))
        yes = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='no'", (prono_id,))
        no = c.fetchone()[0]

        conn.close()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"👍 {yes}", callback_data=f"vote_yes_{prono_id}"),
                InlineKeyboardButton(f"👎 {no}", callback_data=f"vote_no_{prono_id}")
            ],
            [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
        ])

        await query.edit_message_reply_markup(reply_markup=keyboard)

# ==================== HANDLE PROOF ====================
async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "cid" not in context.user_data:
        return await update.message.reply_text("❌ Aucune commande en cours. /start")

    cid = context.user_data["cid"]
    product = context.user_data.get("product", "Produit inconnu")

    try:
        await update.message.forward(ADMIN_ID)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Valider", callback_data=f"validate_{cid}")]
        ])

        await context.bot.send_message(
            ADMIN_ID,
            f"🛒 Commande #{cid}\nProduit : {product}\nUtilisateur : @{update.effective_user.username or update.effective_user.first_name}",
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(e)

    await update.message.reply_text("✅ Preuve envoyée à l'admin")
    context.user_data.clear()

# ==================== PRONO COMMANDES ====================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat) VALUES (?, ?)", (texte, "attente"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Pronostic ajouté")

async def result_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    result = context.args[0]

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE pronos SET resultat=? WHERE id=(SELECT id FROM pronos ORDER BY id DESC LIMIT 1)", (result,))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Résultat mis à jour")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM pronos WHERE resultat='win'")
    win = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM pronos WHERE resultat='lose'")
    lose = c.fetchone()[0]

    total = win + lose
    rate = (win / total * 100) if total > 0 else 0

    conn.close()

    await update.message.reply_text(
        f"📊 Stats pronostics\n\n"
        f"✅ Gagnés : {win}\n"
        f"❌ Perdus : {lose}\n"
        f"📈 Winrate : {rate:.1f}%"
    )

# ==================== MAIN ====================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("result", result_prono))
    app.add_handler(CommandHandler("stats", stats))

    print("✅ Bot lancé FULL VERSION + VOTES")
    app.run_polling()
