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

# ================= DB =================
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

    try:
        c.execute("ALTER TABLE pronos ADD COLUMN type TEXT DEFAULT 'prono'")
    except:
        pass

    conn.commit()
    conn.close()

# ================= PRODUITS =================
PRODUITS = {
    "mcdo": [("Cagnotte 50-74 pts", 2.0), ("Cagnotte 75-99 pts", 3.5)],
    "abo": [("Netflix", 5.0)],
    "snap": [("Snap Tech", 25.0)],
    "tech": [("Uber Tech", 20.0)]
}

# ================= MENUS =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo", callback_data="menu_mcdo")],
        [InlineKeyboardButton("📺 Abos", callback_data="menu_abo")],
        [InlineKeyboardButton("👻 Snap", callback_data="menu_snap")],
        [InlineKeyboardButton("📱 Tech", callback_data="menu_tech")],
        [InlineKeyboardButton("⚽️ Pronostics", callback_data="menu_prono")]
    ])

def prono_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽️ Prono du jour", callback_data="menu_prono_prono")],
        [InlineKeyboardButton("🎟 Ticket du jour", callback_data="menu_prono_ticket")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔥 Bienvenue"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ================= BUTTONS =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # ===== FIX MENU PRONO =====
    if data == "menu_prono":
        await query.edit_message_text(
            "⚽️ Choisis une catégorie",
            reply_markup=prono_menu()
        )
        return

    # ===== PRONO DU JOUR =====
    elif data == "menu_prono_prono":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT id, texte FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        prono_id = 0
        texte = "Aucun prono"

        if row:
            prono_id, texte = row

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='yes'", (prono_id,))
        yes = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM votes WHERE prono_id=? AND vote='no'", (prono_id,))
        no = c.fetchone()[0]

        conn.close()

        await query.edit_message_text(
            f"⚽️ PRONO DU JOUR\n\n{texte}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"👍 {yes}", callback_data=f"vote_yes_{prono_id}"),
                    InlineKeyboardButton(f"👎 {no}", callback_data=f"vote_no_{prono_id}")
                ],
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
            ])
        )

    # ===== TICKET DU JOUR =====
    elif data == "menu_prono_ticket":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        texte = "Aucun ticket"

        if row:
            texte = row[0]

        conn.close()

        await query.edit_message_text(
            f"🎟 TICKET DU JOUR\n\n{texte}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
            ])
        )

    # ===== BACK =====
    elif data == "back":
        await start(update, context)

    # ===== SHOP =====
    elif data.startswith("menu_"):
        cat = data.split("_")[1]

        produits = PRODUITS[cat]

        kb = [
            [InlineKeyboardButton(f"{p} - {x}€", callback_data=f"buy_{cat}_{i}")]
            for i, (p, x) in enumerate(produits)
        ]

        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])

        await query.edit_message_text("📦 Produits", reply_markup=InlineKeyboardMarkup(kb))

    # ===== BUY =====
    elif data.startswith("buy_"):
        _, cat, i = data.split("_")
        i = int(i)

        nom, prix = PRODUITS[cat][i]

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?,?,?,?)",
                  (user.id, user.username or "user", nom, prix))
        conn.commit()
        cid = c.lastrowid
        conn.close()

        await query.edit_message_text(f"✅ Commande #{cid}\n{nom} - {prix}€")

    # ===== VOTES =====
    elif data.startswith("vote_"):
        _, vote, prono_id = data.split("_")
        prono_id = int(prono_id)

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("DELETE FROM votes WHERE user_id=? AND prono_id=?", (user.id, prono_id))
        c.execute("INSERT INTO votes (user_id, prono_id, vote) VALUES (?,?,?)",
                  (user.id, prono_id, vote))

        conn.commit()
        conn.close()

        await query.answer("Vote OK")

# ================= ADMIN =================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?,?,?)",
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
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?,?,?)",
              (texte, "attente", "ticket
