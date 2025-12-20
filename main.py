import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="pagamento")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]
    await update.message.reply_text(
        "🔥 *Bem-vindo ao Dark Access VIP*\n\nEscolha uma opção:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "planos":
        keyboard = [
            [InlineKeyboardButton("💎 VIP Mensal - R$29,90", callback_data="vip_mensal")],
            [InlineKeyboardButton("🔥 VIP Trimestral - R$79,90", callback_data="vip_tri")]
        ]
        await query.edit_message_text(
            "📌 *Escolha seu plano:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "vip_mensal":
        await query.edit_message_text(
            "💎 *VIP Mensal*\n\n"
            "Valor: *R$29,90*\n\n"
            "💳 Pix ou Cartão\n"
            "Envie o comprovante após pagar.",
            parse_mode="Markdown"
        )

    elif query.data == "vip_tri":
        await query.edit_message_text(
            "🔥 *VIP Trimestral*\n\n"
            "Valor: *R$79,90*\n\n"
            "💳 Pix ou Cartão\n"
            "Envie o comprovante após pagar.",
            parse_mode="Markdown"
        )

    elif query.data == "pagamento":
        await query.edit_message_text(
            "💳 *Pagamento*\n\n"
            "📌 Pix: SUA_CHAVE_PIX_AQUI\n"
            "📌 Cartão: LINK_DO_CARTAO\n\n"
            "Após pagar, envie o comprovante.",
            parse_mode="Markdown"
        )

    elif query.data == "ajuda":
        await query.edit_message_text(
            "❓ *Ajuda*\n\n"
            "Após o pagamento, envie o comprovante.",
            parse_mode="Markdown"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu))
    app.run_polling()

if __name__ == "__main__":
    main()
