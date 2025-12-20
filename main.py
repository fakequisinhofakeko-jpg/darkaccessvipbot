async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="pagamento")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]

    reply_markup = InlineKeyboardMarkup(teclado)

    await update.message.reply_text(
        "🔥 *Bem-vindo ao Dark Access VIP*\n\n"
        "Escolha uma opção abaixo:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês – R$24,90", callback_data="vip_1m")],
        [InlineKeyboardButton("🔥 3 Meses – R$64,90", callback_data="vip_3m")],
        [InlineKeyboardButton("👑 Vitalício – R$149,90", callback_data="vip_vitalicio")]
    ]

    reply_markup = InlineKeyboardMarkup(teclado)

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📌 *Escolha seu plano:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )async def pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "💳 *Formas de pagamento disponíveis:*\n\n"
        "✅ Pix\n"
        "✅ Cartão de crédito\n\n"
        "Após o pagamento, envie o comprovante.",
        parse_mode="Markdown"
    )async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "❓ *Precisa de ajuda?*\n\n"
        "Fale com o suporte ou envie sua dúvida aqui.",
        parse_mode="Markdown"
    )application.add_handler(CommandHandler("start", start))

application.add_handler(CallbackQueryHandler(planos, pattern="^planos$"))
application.add_handler(CallbackQueryHandler(pagamento, pattern="^pagamento$"))
application.add_handler(CallbackQueryHandler(ajuda, pattern="^ajuda$"))
