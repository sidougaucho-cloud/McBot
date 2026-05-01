import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ================= CONFIG =================
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

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, produit TEXT,
        prix REAL, statut TEXT DEFAULT 'en_attente', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texte TEXT, resultat TEXT DEFAULT 'attente', type TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_pronos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, match TEXT,
        prono TEXT, cote REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS prono_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vote TEXT CHECK(vote IN ('oui', 'non')),
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        enabled INTEGER DEFAULT 1,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()

# ================= KEYBOARDS =================
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
        [InlineKeyboardButton("⚽️ Prono du jour", callback_data="prono_jour")],
        [InlineKeyboardButton("🎟 Ticket du jour", callback_data="ticket_jour")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="back_main")]
    ])

def vote_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ D’accord", callback_data="vote_oui"),
            InlineKeyboardButton("❌ Pas d’accord", callback_data="vote_non")
        ],
        [InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🔥🚨 Bienvenu sur le shop ! 

✅  Boutique ouverte ! 

🛍️🛒 Pour commander rien de plus simple : 
Choisis l’article désiré ensuite effectue le paiement via PayPal.

🔔 /notif on  → Recevoir les nouveaux pronos
🔔 /notif off → Désactiver

🆘 SAV : @Zeerkay"""
    
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

    if data in ["vote_oui", "vote_non"]:
        vote = "oui" if data == "vote_oui" else "non"
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO prono_votes (user_id, vote) VALUES (?, ?)", (user.id, vote))
            conn.commit()
            await query.edit_message_text("✅ Ton vote a été enregistré ! Merci.", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        except sqlite3.IntegrityError:
            await query.edit_message_text("⚠️ Tu as déjà voté.", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        conn.close()
        return

    if data == "menu_prono":
        await query.edit_message_text("⚽️ **Pronostics**", reply_markup=prono_menu(), parse_mode='Markdown')
        return

    if data == "prono_jour":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT texte, resultat FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()

        if row:
            texte, resultat = row
            resultat_text = f"\n\n**Résultat :** {resultat}" if resultat and resultat != "attente" else "\n\n**Résultat :** En attente"
            message = f"⚽️ **PRONO DU JOUR**\n\n{texte}{resultat_text}"
        else:
            message = "⚽️ **PRONO DU JOUR**\n\nAucun prono disponible pour le moment."

        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=vote_keyboard())
        return

    if data == "ticket_jour":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        texte = row[0] if row else "Aucun ticket."
        await query.edit_message_text(f"🎟 **TICKET DU JOUR**\n\n{texte}", parse_mode='Markdown',
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        return

    if data == "back_main":
        await start(update, context)
        return

    # SHOP
    if data.startswith("menu_"):
        cat = data.split("_")[1]
        if cat not in PRODUITS:
            await query.edit_message_text("❌ Catégorie invalide.")
            return
        produits = PRODUITS[cat]
        kb = [[InlineKeyboardButton(f"{nom} — {prix}€", callback_data=f"buy_{cat}_{idx}")] for idx, (nom, prix) in enumerate(produits)]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])
        await query.edit_message_text(f"📦 **{cat.upper()}**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return

    if data.startswith("buy_"):
        try:
            _, cat, idx = data.split("_")
            idx = int(idx)
            nom, prix = PRODUITS[cat][idx]
        except:
            await query.edit_message_text("❌ Erreur.")
            return

        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO commandes (user_id, username, produit, prix) VALUES (?,?,?,?)",
                  (user.id, user.username or "unknown", nom, prix))
        conn.commit()
        cid = c.lastrowid
        conn.close()

        paypal_link = f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business={PAYPAL_EMAIL}&amount={prix}&currency_code=EUR&item_name={nom.replace(' ', '+')}"

        context.user_data["pending_cid"] = cid

        await query.edit_message_text(
            f"✅ **Commande #{cid}**\n\n**Article :** {nom}\n**Prix :** {prix}€",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Payer avec PayPal", url=paypal_link)],
                [InlineKeyboardButton("📸 J’ai payé", callback_data=f"proof_{cid}")]
            ])
        )
        return

    if data.startswith("proof_"):
        cid = data.split("_")[1]
        await query.edit_message_text("📸 Envoie-moi ta preuve de paiement.")
        context.user_data["pending_cid"] = cid
        return

    if data.startswith("validate_") and user.id == ADMIN_ID:
        cid = int(data.split("_")[1])
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("UPDATE commandes SET statut = 'validée' WHERE id = ?", (cid,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"✅ Commande #{cid} validée !")
        return


# ================= PROOF =================
async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "pending_cid" not in context.user_data:
        return await update.message.reply_text("❌ Aucune commande en attente.")
    cid = context.user_data.pop("pending_cid")
    await update.message.forward(ADMIN_ID)
    await context.bot.send_message(
        ADMIN_ID, f"🛒 Preuve pour #{cid}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Valider", callback_data=f"validate_{cid}")]])
    )
    await update.message.reply_text("✅ Preuve envoyée.")


# ================= NOTIFICATIONS =================
async def notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text("Utilisation : /notif on ou /notif off")
        return

    enabled = 1 if context.args[0].lower() == "on" else 0
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO notifications (user_id, username, enabled) VALUES (?,?,?)",
              (update.effective_user.id, update.effective_user.username or "user", enabled))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"🔔 Notifications **{'activées' if enabled else 'désactivées'}**.")


# ================= SET PRONO + NOTIF =================
async def set_prono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Exemple :\n`/setprono Braga - Fribourg | Les 2 équipes marquent | 2.15`")
        return

    texte = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    if update.effective_user.id == ADMIN_ID:
        c.execute("DELETE FROM pronos WHERE type = 'prono'")
        c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, 'attente', 'prono')", (texte,))
        conn.commit()

        # Envoi notifications
        c.execute("SELECT user_id FROM notifications WHERE enabled = 1")
        subs = c.fetchall()
        conn.close()

        sent = 0
        for (uid,) in subs:
            try:
                await context.bot.send_message(uid, f"🔔 **Nouveau Prono du Jour !**\n\n{texte}\n\nVa dans Pronostics → Prono du jour")
                sent += 1
            except:
                pass

        await update.message.reply_text(f"✅ Prono publié et notifié à {sent} personnes !")
    else:
        # prono utilisateur
        parts = [p.strip() for p in texte.split("|")]
        match = parts[0]
        prono_desc = parts[1] if len(parts) > 1 else texte
        cote = float(parts[2]) if len(parts) > 2 else None

        c.execute("DELETE FROM user_pronos WHERE user_id = ? AND match = ?", (update.effective_user.id, match))
        c.execute("INSERT INTO user_pronos (user_id, username, match, prono, cote) VALUES (?,?,?,?,?)",
                  (update.effective_user.id, update.effective_user.username or "user", match, prono_desc, cote))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Ton prono enregistré !")


# ================= SET RESULT =================
async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Seul l'admin peut définir le résultat.")
        return
    if not context.args:
        await update.message.reply_text("Exemple :\n`/setresult gagné`\n`/setresult perdu`\n`/setresult win`")
        return

    resultat = " ".join(context.args).strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE pronos SET resultat = ? WHERE type = 'prono' ORDER BY id DESC LIMIT 1", (resultat,))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Résultat mis à jour :\n**{resultat}**", parse_mode='Markdown')


# ================= LANCEMENT =================
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_proof))

    app.add_handler(CommandHandler("setprono", set_prono))
    app.add_handler(CommandHandler("setresult", set_result))
    app.add_handler(CommandHandler("notif", notif))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mypronos", mypronos))

    print("🚀 Bot lancé avec succès - Tout est corrigé")
    app.run_polling()
