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
        type TEXT DEFAULT 'prono',
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        prono_id INTEGER,
        vote TEXT
    )
    """)

    # sécurité upgrade DB
    try:
        c.execute("ALTER TABLE pronos ADD COLUMN type TEXT DEFAULT 'prono'")
    except:
        pass

    conn.commit()
    conn.close()

# ==================== DB FUNCTIONS ====================
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

# ==================== PRODUITS ====================
PRODUITS = {
    "mcdo": [
        ("Cagnotte 50-74 pts", 2.0),
        ("Cagnotte 75-99 pts", 3.5),
        ("Cagnotte 100-124 pts", 4.5),
        ("Cagnotte 125-174 pts", 6.5),
    ],
    "abo": [
        ("Netflix", 5.0),
        ("Deezer Premium", 5.0),
    ],
    "snap": [
        ("Tech Snapchat +", 25.0),
    ],
    "tech": [
        ("Tech Uber Eat", 20.0),
    ]
}

# ==================== MENUS ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abonnements", callback_data="menu_abo")],
        [InlineKeyboardButton("👻 Snapchat", callback_data="menu_snap")],
        [InlineKeyboardButton("📱 Tech", callback_data="menu_tech")],
        [InlineKeyboardButton("⚽️ Pronostics", callback_data="menu_prono")]
    ])

def prono_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽️ Prono du jour", callback_data="menu_prono_prono")],
        [InlineKeyboardButton("🎟 Ticket du jour", callback_data="menu_prono_ticket")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
    ])

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 Bienvenue sur le shop !\n\n"
        "🛍️ Choisis une catégorie"
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

    # ================= MENU =================
    if data.startswith("menu_"):
        cat = data.split("_")[1]

        if cat == "prono":
            await query.edit_message_text(
                "⚽️ Choisis une catégorie",
                reply_markup=prono_menu()
            )
            return

        produits = PRODUITS[cat]
        text = f"📦 Catégorie {cat}"

        kb = []
        for i, (nom, prix) in enumerate(produits):
            kb.append([InlineKeyboardButton(f"{nom} - {prix}€", callback_data=f"buy_{cat}_{i}")])

        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    # ================= PRONO =================
    elif data == "menu_prono_prono":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT id, texte FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        prono_id = 0
        texte = "Aucun prono du jour"

        if row:
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
            [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
        ])

        await query.edit_message_text(f"⚽️ PRONO DU JOUR\n\n{texte}", reply_markup=keyboard)

    elif data == "menu_prono_ticket":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        texte = "Aucun ticket du jour"

        if row:
            texte = row[0]

        conn.close()

        await query.edit_message_text(
            f"🎟 TICKET DU JOUR\n\n{texte}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
            ])
        )

    # ================= BACK =================
    elif data == "back":
        await start(update, context)

    # ================= BUY =================
    elif data.startswith("buy_"):
        _, cat, index = data.split("_")
        index = int(index)

        nom, prix = PRODUITS[cat][index]

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO commandes (user_id, username, produit, prix)
            VALUES (?, ?, ?, ?)
        """, (user.id, user.username or "user", nom, prix))
        conn.commit()
        cid = c.lastrowid
        conn.close()

        context.user_data["cid"] = cid
        context.user_data["product"] = nom

        await query.edit_message_text(
            f"✅ Commande #{cid}\nProduit : {nom}\nPrix : {prix}€"
        )

# ==================== PRONO COMMANDS ====================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, ?, ?)",
              (texte, "attente", "prono"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Prono ajouté")

async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, ?, ?)",
              (texte, "attente", "ticket"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Ticket ajouté")

# ==================== MAIN ====================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))

    print("🚀 Bot FULL VERSION lancé")
    app.run_polling()
