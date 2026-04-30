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

PAYPAL_EMAIL = "Sidou.gaucho@gmail.com"

logging.basicConfig(level=logging.INFO)

# ================= PRODUITS =================
PRODUITS = {
    "mcdo": [
        ("Cagnotte 50-74 pts", 2.0), ("Cagnotte 75-99 pts", 3.5),
        ("Cagnotte 100-124 pts", 4.5), ("Cagnotte 125-174 pts", 6.5),
        ("Cagnotte 175-199 pts", 8.0), ("Cagnotte 200-249 pts", 9.5),
        ("Cagnotte 250-299 pts", 10.5), ("Cagnotte 300-324 pts", 11.5),
        ("Cagnotte 325-374 pts", 12.0), ("Cagnotte 375-400 pts", 13.0),
        ("Cagnotte 400-499 pts", 14.0), ("Cagnotte 500-599 pts", 19.0),
    ],
    "abo": [("Netflix", 5.0), ("Deezer Premium", 5.0)],
    "snap": [("Tech Snapchat +", 25.0), ("Tech erreur SS06", 20.0)],
    "tech": [("Tech Uber Eat", 20.0)]
}

# ================= DB =================
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, produit TEXT,
        prix REAL, statut TEXT DEFAULT 'en_attente'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT, resultat TEXT, type TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, match TEXT,
        prono TEXT, cote REAL, date TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()

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
    text = "🔥🚨 Bienvenue sur le shop !\n\n✅ Boutique ouverte\n\n🛍️ Choisis l’article puis paie via PayPal.\n\n🆘 SAV : @Zeerkay"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_prono":
        await query.edit_message_text("⚽️ Pronostics", reply_markup=prono_menu())
        return

    # ================= PRONO DU JOUR =================
    if data == "menu_prono_prono":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT texte, resultat FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()

        if row:
            texte, resultat = row
            resultat_text = f"\n\n**Résultat :** {resultat}" if resultat and resultat != "attente" else ""
            message = f"⚽️ **PRONO DU JOUR**\n\n{texte}{resultat_text}"
        else:
            message = "⚽️ **PRONO DU JOUR**\n\nAucun prono pour le moment."

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]])
        )
        return

    # ================= TICKET DU JOUR =================
    if data == "menu_prono_ticket":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        texte = row[0] if row else "Aucun ticket"
        await query.edit_message_text(f"🎟 **TICKET DU JOUR**\n\n{texte}", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        return

    if data == "back":
        await start(update, context)
        return

    # ================= SHOP =================
    if data.startswith("menu_"):
        cat = data.split("_")[1]
        produits = PRODUITS[cat]
        kb = [[InlineKeyboardButton(f"{p} - {x}€", callback_data=f"buy_{cat}_{i}")] for i, (p, x) in enumerate(produits)]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back")])
        await query.edit_message_text("📦 Produits", reply_markup=InlineKeyboardMarkup(kb))

    if data.startswith("buy_"):
        _, cat, i = data.split("_")
        i = int(i)
        nom, prix = PRODUITS[cat][i]

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?,?,?,?)",
                  (query.from_user.id, query.from_user.username or "user", nom, prix))
        conn.commit()
        cid = c.lastrowid
        conn.close()

        paypal_link = f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business={PAYPAL_EMAIL}&amount={prix}&currency_code=EUR"
        context.user_data["cid"] = cid

        await query.edit_message_text(
            f"✅ Commande #{cid}\n\n{nom} - {prix}€\n\n💳 Paiement PayPal",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Payer PayPal", url=paypal_link)],
                [InlineKeyboardButton("📸 J’ai payé", callback_data=f"proof_{cid}")]
            ])
        )

# ================= PROOF =================
async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "cid" not in context.user_data:
        return await update.message.reply_text("❌ Aucune commande en cours.")
    cid = context.user_data["cid"]
    await update.message.forward(ADMIN_ID)
    await context.bot.send_message(ADMIN_ID, f"🛒 Commande #{cid} - preuve reçue",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Valider", callback_data=f"validate_{cid}")]]))
    await update.message.reply_text("✅ Preuve envoyée à l'admin")
    context.user_data.clear()

# ================= SET PRONO =================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Exemple :\n`/setprono Braga - Fribourg | Les 2 équipes marquent | 2`")
        return

    texte = " ".join(context.args)

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if update.effective_user.id == ADMIN_ID:
        # Admin → Prono du jour (table pronos)
        c.execute("DELETE FROM pronos WHERE type = 'prono'")
        c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, 'attente', 'prono')", (texte,))
        await update.message.reply_text("✅ Prono du jour mis à jour avec succès !")
    else:
        # Utilisateur normal → prono personnel
        parts = [p.strip() for p in texte.split("|")]
        match = parts[0]
        prono_desc = parts[1] if len(parts) > 1 else texte
        cote = float(parts[2]) if len(parts) > 2 else None

        c.execute("DELETE FROM user_pronos WHERE user_id = ? AND match LIKE ?", 
                  (update.effective_user.id, f"%{match}%"))
        c.execute("INSERT INTO user_pronos (user_id, username, match, prono, cote) VALUES (?,?,?,?,?)",
                  (update.effective_user.id, update.effective_user.username or "user", match, prono_desc, cote))
        await update.message.reply_text(f"✅ Ton prono a été enregistré !")

    conn.commit()
    conn.close()

# ================= AUTRES COMMANDES =================
async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Seul l'admin peut définir le résultat.")
        return
    if not context.args:
        await update.message.reply_text("Exemple : `/setresult gagné` ou `/setresult perdu` ou `/setresult 2-1`")
        return

    resultat = " ".join(context.args).strip()
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE pronos SET resultat = ? WHERE type = 'prono' ORDER BY id DESC LIMIT 1", (resultat,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Résultat mis à jour : **{resultat}**")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT texte, resultat FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    prono = row[0] if row else "Aucun prono"
    res = row[1] if row and row[1] else "En attente"
    c.execute("SELECT COUNT(DISTINCT user_id) FROM user_pronos")
    participants = c.fetchone()[0] or 0

    await update.message.reply_text(
        f"📊 **Stats Pronos**\n\n"
        f"**Prono du jour :** {prono}\n"
        f"**Résultat :** {res}\n\n"
        f"👥 Participants : {participants}",
        parse_mode='Markdown'
    )
    conn.close()

async def mypronos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT match, prono, cote FROM user_pronos WHERE user_id = ? ORDER BY date DESC", 
              (update.effective_user.id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Tu n'as encore enregistré aucun prono.")
        return

    text = "📋 **Tes pronos :**\n\n"
    for match, prono, cote in rows:
        text += f"• {match}\n  → {prono} @ {cote if cote else '?'}\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    texte = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?,?,?)", (texte, "attente", "ticket"))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Ticket ajouté")

# ================= LANCEMENT =================
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setticket", set_ticket))
    app.add_handler(CommandHandler("setresult", set_result))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mypronos", mypronos))

    print("🚀 Bot lancé avec succès - Prono du jour corrigé")
    app.run_polling()
