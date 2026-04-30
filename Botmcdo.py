async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Seuls les admins peuvent définir le résultat.")
        return

    if not context.args:
        await update.message.reply_text(
            "📌 **Format de la commande :**\n\n"
            "`/setresult gagné`\n"
            "`/setresult perdu`\n"
            "`/setresult nul`\n"
            "`/setresult 2-1` (score exact)\n\n"
            "Exemple : `/setresult gagné`"
        )
        return

    resultat = " ".join(context.args).strip()

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()

    c.execute("""
        UPDATE pronos 
        SET resultat = ? 
        WHERE type = 'prono' 
        ORDER BY id DESC 
        LIMIT 1
    """, (resultat,))

    if c.rowcount > 0:
        await update.message.reply_text(f"✅ Résultat du prono du jour mis à jour :\n**{resultat}**")
    else:
        await update.message.reply_text("❌ Aucun prono du jour trouvé.")

    conn.commit()
    conn.close()
