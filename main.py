import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="pagamento")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]

    await update.message.reply_text(
        "🔥 *Bem-vindo ao Dark Access VIP*\n\n"
        "Escolha uma opção abaixo:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ---------- PLANOS ----------
async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês — R$24,90", callback_data="vip_1m")],
        [InlineKeyboardButton("🔥 3 Meses — R$64,90", callback_data="vip_3m")],
        [InlineKeyboardButton("👑 Vitalício — R$149,90", callback_data="vip_vitalicio")]
    ]

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ---------- PAGAMENTO ----------
async def pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "💳 *Formas de pagamento*\n\n"
        "✅ Pix\n"
        "✅ Cartão de crédito\n\n"
        "Após o pagamento, envie o comprovante.",
        parse_mode="Markdown"
    )

# ---------- AJUDA ----------
async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "❓ *Ajuda*\n\n"
        "Em caso de dúvidas, entre em contato com o suporte.",
        parse_mode="Markdown"
    )

# ---------- MAIN ----------
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(planos, pattern="^planos$"))
    application.add_handler(CallbackQueryHandler(pagamento, pattern="^pagamento$"))
    application.add_handler(CallbackQueryHandler(ajuda, pattern="^ajuda$"))

    application.run_polling()

if __name__ == "__main__":
    main()
