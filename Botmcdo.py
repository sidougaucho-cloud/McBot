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
        texte TEXT, resultat TEXT, type TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
Choisis l’article désiré ensuite effectue le paiement via PayPal. L’interface a été pensée simple pour plus de fluidité 

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

    # ====================== VOTES ======================
    if data == "vote_oui" or data == "vote_non":
        vote = "oui" if data == "vote_oui" else "non"
        
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO prono_votes (user_id, vote) VALUES (?, ?)", (user.id, vote))
            conn.commit()
            await query.edit_message_text("✅ Ton vote a été enregistré ! Merci.", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        except sqlite3.IntegrityError:
            await query.edit_message_text("⚠️ Tu as déjà voté pour ce prono.", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]]))
        conn.close()
        return

    # ====================== PRONOS ======================
    if data == "menu_prono":
        await query.edit_message_text("⚽️ **Pronostics**", reply_markup=prono_menu(), parse_mode='Markdown')
        return

    if data == "prono_jour":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()

        # Prono actuel
        c.execute("SELECT texte, resultat FROM pronos WHERE type='prono' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()

        if row:
            texte, resultat = row
            resultat_text = f"\n\n**Résultat :** {resultat}" if resultat and resultat != "attente" else "\n\n**Résultat :** En attente"
        else:
            texte = "Aucun prono disponible pour le moment."
            resultat_text = ""

        # Statistiques des anciens pronos
        c.execute("SELECT resultat FROM pronos WHERE type='prono' AND resultat != 'attente' AND resultat IS NOT NULL")
        past_results = c.fetchall()

        gagnés = 0
        perdus = 0

        for (res,) in past_results:
            res_lower = (res or "").lower()
            if any(word in res_lower for word in ["gagn", "gagné", "win", "victoire", "1", "2", "3", "oui", "marquent"]):
                gagnés += 1
            else:
                perdus += 1

        total_termines = gagnés + perdus
        if total_termines > 0:
            pct_gagne = round((gagnés / total_termines) * 100, 1)
            pct_perdu = round((perdus / total_termines) * 100, 1)
            stats_text = f"\n\n📊 **Stats anciens pronos :**\n✅ Gagnés : {gagnés} ({pct_gagne}%)\n❌ Perdus : {perdus} ({pct_perdu}%)"
        else:
            stats_text = "\n\n📊 **Stats anciens pronos :** Aucun prono terminé pour le moment."

        message = f"⚽️ **PRONO DU JOUR**\n\n{texte}{resultat_text}{stats_text}"

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=vote_keyboard()
        )
        conn.close()
        return

    if data == "ticket_jour":
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT texte FROM pronos WHERE type='ticket' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        texte = row[0] if row else "Aucun ticket du jour pour le moment."
        await query.edit_message_text(
            f"🎟 **TICKET DU JOUR**\n\n{texte}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu_prono")]])
        )
        return

    if data == "back_main":
        await start(update, context)
        return

    # ====================== SHOP ======================
    if data.startswith("menu_"):
        cat = data.split("_")[1]
        if cat not in PRODUITS:
            await query.edit_message_text("❌ Catégorie invalide.")
            return

        produits = PRODUITS[cat]
        kb = [[InlineKeyboardButton(f"{nom} — {prix}€", callback_data=f"buy_{cat}_{idx}")] 
              for idx, (nom, prix) in enumerate(produits)]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="back_main")])

        await query.edit_message_text(f"📦 **{cat.upper()}**", 
                                     reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return

    if data.startswith("buy_"):
        try:
            _, cat, idx = data.split("_")
            idx = int(idx)
            nom, prix = PRODUITS[cat][idx]
        except:
            await query.edit_message_text("❌ Erreur lors de la sélection du produit.")
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
            f"✅ **Commande #{cid}**\n\n**Article :** {nom}\n**Prix :** {prix}€\n\n💳 Paiement PayPal :",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Payer avec PayPal", url=paypal_link)],
                [InlineKeyboardButton("📸 J’ai payé", callback_data=f"proof_{cid}")]
            ])
        )
        return

    if data.startswith("proof_"):
        cid = data.split("_")[1]
        await query.edit_message_text("📸 Envoie-moi maintenant ta preuve de paiement (photo).")
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
        ADMIN_ID,
        f"🛒 Preuve reçue pour la commande #{cid}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Valider", callback_data=f"validate_{cid}")]])
    )
    await update.message.reply_text("✅ Preuve envoyée à l'admin.")


# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("""SELECT texte, resultat, date 
                 FROM pronos 
                 WHERE type = 'prono' 
                 ORDER BY id DESC""")
    all_pronos = c.fetchall()

    if not all_pronos:
        await update.message.reply_text("📊 Aucun prono disponible pour le moment.")
        conn.close()
        return

    total_pronos = len(all_pronos)
    gagnés = 0
    perdus = 0
    en_cours = 0

    details = ""

    for texte, resultat, date in all_pronos:
        if resultat == "attente":
            en_cours += 1
            status = "⏳ En cours"
        elif resultat and any(word in resultat.lower() for word in ["gagn", "gagné", "win", "1", "2", "3", "oui", "marquent", "victoire"]):
            gagnés += 1
            status = "✅ Gagné"
        else:
            perdus += 1
            status = "❌ Perdu"

        details += f"🗓 {date[:10]} | {status}\n{texte[:70]}{'...' if len(texte) > 70 else ''}\n\n"

    if (gagnés + perdus) > 0:
        pourc_gagne = round((gagnés / (gagnés + perdus)) * 100, 1)
        pourc_perdu = round((perdus / (gagnés + perdus)) * 100, 1)
    else:
        pourc_gagne = pourc_perdu = 0

    message = f"""📊 **Statistiques Pronos du Jour**

**Total pronos :** {total_pronos}
**En cours :** {en_cours}

✅ **Gagnés :** {gagnés} ({pourc_gagne}%)
❌ **Perdus :** {perdus} ({pourc_perdu}%)

📋 **Détails :**
{details}"""

    await update.message.reply_text(message, parse_mode='Markdown')
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


# ================= AUTRES COMMANDES ADMIN =================
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
        await update.message.reply_text("✅ Prono du jour mis à jour !")
    else:
        parts = [p.strip() for p in texte.split("|")]
        match = parts[0]
        prono_desc = parts[1] if len(parts) > 1 else texte
        cote = float(parts[2]) if len(parts) > 2 else None

        c.execute("DELETE FROM user_pronos WHERE user_id = ? AND match = ?", (update.effective_user.id, match))
        c.execute("INSERT INTO user_pronos (user_id, username, match, prono, cote) VALUES (?,?,?,?,?)",
                  (update.effective_user.id, update.effective_user.username or "user", match, prono_desc, cote))
        await update.message.reply_text(f"✅ Ton prono enregistré !")

    conn.commit()
    conn.close()


async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Seul l'admin peut définir le résultat.")
        return
    if not context.args:
        await update.message.reply_text("Exemple : `/setresult gagné` ou `/setresult perdu` ou `/setresult 2-1`")
        return

    resultat = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE pronos SET resultat = ? WHERE type = 'prono' ORDER BY id DESC LIMIT 1", (resultat,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Résultat mis à jour : **{resultat}**")


async def set_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    texte = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO pronos (texte, resultat, type) VALUES (?, 'attente', 'ticket')", (texte,))
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
    app.add_handler(CommandHandler("setresult", set_result))
    app.add_handler(CommandHandler("setticket", set_ticket))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mypronos", mypronos))

    print("🚀 Bot lancé avec succès - Stats anciens pronos ajoutées dans Prono du jour !")
    app.run_polling()
