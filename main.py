import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="pagamento")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔥 *Bem-vindo ao Dark Access VIP*\n\n"
        "Escolha uma opção abaixo:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "planos":
        await query.edit_message_text(
            "📌 *Planos disponíveis*\n\n"
            "• VIP Mensal\n"
            "• VIP Trimestral\n\n"
            "_Em breve valores._",
            parse_mode="Markdown"
        )

    elif query.data == "pagamento":
        await query.edit_message_text(
            "💳 *Formas de pagamento*\n\n"
            "• Pix\n"
            "• Cartão\n\n"
            "_Pagamento será liberado em breve._",
            parse_mode="Markdown"
        )

    elif query.data == "ajuda":
        await query.edit_message_text(
            "❓ *Ajuda*\n\n"
            "Em caso de dúvidas, aguarde ou fale com o suporte.",
            parse_mode="Markdown"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu))

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
