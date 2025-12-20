async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês - R$24,90", callback_data="vip_1m")],
        [InlineKeyboardButton("🔥 3 Meses - R$64,90", callback_data="vip_3m")],
        [InlineKeyboardButton("👑 Vitalício - R$149,90", callback_data="vip_vitalicio")]
    ]

    reply_markup = InlineKeyboardMarkup(teclado)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "📌 Escolha seu plano:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📌 Escolha seu plano:",
            reply_markup=reply_markup
        )
