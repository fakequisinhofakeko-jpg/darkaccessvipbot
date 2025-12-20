import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- Telegram Bot ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔓 Planos", callback_data="planos")],
        [InlineKeyboardButton("💳 Pagar", callback_data="pagar")],
        [InlineKeyboardButton("📩 Suporte", url="https://t.me/DarkAccessVIPBot")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔒 Dark Access VIP\n\n"
        "Conteúdo exclusivo.\n"
        "🚫 Apenas para maiores de 18 anos.\n\n"
        "Escolha uma opção abaixo:",
        reply_markup=reply_markup
    )

# ---------- Flask (para manter online / webhook futuro) ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "DarkAccessVIPBot ativo."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
