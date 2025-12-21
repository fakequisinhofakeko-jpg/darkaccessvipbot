import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# =========================
# CONFIGURAÇÕES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID DO GRUPO VIP
VIP_GROUP_ID = -1003513694224

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Dark Access VIP\n\n"
        "Use /linkvip para testar o acesso ao grupo."
    )

# =========================
# GERAR LINK DO GRUPO (TESTE)
# =========================
async def gerar_link_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=VIP_GROUP_ID,
            member_limit=1,
            name="Acesso VIP"
        )

        await update.message.reply_text(
            "✅ Link VIP gerado com sucesso:\n\n"
            f"{invite.invite_link}\n\n"
            "⚠️ Link válido para 1 pessoa."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Erro ao gerar link do grupo.\n\n"
            f"Detalhes:\n{e}"
        )

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("linkvip", gerar_link_vip))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
