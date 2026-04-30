import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

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
        statut TEXT DEFAULT 'en_attente'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT,
        resultat TEXT,
        type TEXT
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

    conn.commit()
    conn.close()

# ================= PRODUITS (RESTORED) =================
PRODUITS = {
    "mcdo": [
        ("Cagnotte 50-74 pts", 2.0),
        ("Cagnotte 75-99 pts", 3.5),
        ("Cagnotte 100-124 pts", 4.5),
        ("Cagnotte 125-174 pts", 6.5),
        ("Cagnotte 175-199 pts", 8.0),
        ("Cagnotte 200-249 pts", 9.5),
        ("Cagnotte 250-299 pts", 10.5),
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

# ================= MENUS =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 McDo Cagnottes", callback_data="menu_mcdo")],
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

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔥 Bienvenue sur le shop"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # ===== MENU PRONO FIX =====
    if data == "menu_prono":
        await query.edit_message_text(
            "⚽️ Choisis une catégorie",
            reply_markup=prono_menu()
        )
        return

    # ===== PRONO =====
    if data == "menu_prono_prono":
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
        return

    # ===== TICKET =====
    if data == "menu_prono_ticket":
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
        return

    # ===== BACK =====
    if data == "back":
        await start(update, context)
        return

    # ===== SHOP =====
    if data.startswith("menu_"):
        cat = data.split("_")[1]
        produits = PRODUITS[cat]

        kb = [
            [InlineKeyboardButton(f"{p} - {x}€", callback_data=f"buy_{cat}_{i}")]
            for i, (p, x) in enumerate(produits)
        ]

        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])

        await query.edit_message_text("📦 Produits", reply_markup=InlineKeyboardMarkup(kb))

    # ===== BUY =====
    if data.startswith("buy_"):
        _, cat, i = data.split("_")
        i = int(i)

        nom, prix = PRODUITS[cat][i]

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?,?,?,?)",
                  (user.id, user.username or "user", nom, prix))
        conn.commit()
        conn.close()

        await query.edit_message_text(f"✅ Commande\n{nom} - {prix}€")

    # ===== VOTES =====
    if data.startswith("vote_"):
        _, vote, prono_id = data.split("_")
        prono_id = int(prono_id)

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        c.execute("DELETE FROM votes WHERE user_id=? AND prono_id=?", (user.id, prono_id))
        c.execute("INSERT INTO votes (user_id, prono_id, vote) VALUES (?,?,?)",
                  (user.id, prono_id, vote))

        conn.commit()
        conn.close()

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
              (texte, "attente", "ticket"))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Ticket ajouté")

# ================= MAIN =================
if __name__ == "__main__":
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))

    print("🚀 BOT FULL RESTORED + FIXED")
    app.run_polling()
