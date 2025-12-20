import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagamento", url="https://t.me/AnimeAfterDarkSuportebot")],
        [InlineKeyboardButton("🛎 Suporte", url="https://t.me/AnimeAfterDarkSuportebot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔞 *Dark Access VIP*\n\n"
        "Conteúdo adulto exclusivo.\n"
        "Acesso apenas para maiores de 18 anos.\n\n"
        "Escolha uma opção abaixo 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
