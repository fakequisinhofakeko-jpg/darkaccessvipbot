import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789            # SEU ID
GROUP_ID = -1003513694224       # SEU GRUPO
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90},
}

pagamentos_pendentes = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🔞 AVISO LEGAL\n"
        "Conteúdo adulto +18\n\n"
        "💳 Pagamento via PIX\n"
        "🔒 Acesso VIP"
    )

    teclado = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="plano_vip3")],
    ]

    await update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90},
    "vip_vitalicio": {"nome": "VIP Vitalício", "valor": 149.90},
}

pagamentos_pendentes = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🔞 AVISO +18\n"
        "Conteúdo adulto do tipo anime/ilustrado.\n"
        "Ao continuar, você confirma ser maior de 18 anos.\n\n"
        "💳 Pagamento via PIX\n"
        "🔒 Acesso VIP"
    )

    teclado = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="plano_vip3")],
        [InlineKeyboardButton("💎 VIP Vitalício", callback_data="plano_vip_vitalicio")],
    ]

    await update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= ESCOLHER PLANO =================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plano_id = q.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    pagamentos_pendentes[q.from_user.id] = plano

    texto = (
        f"📦 {plano['nome']}\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"🔑 PIX Copia e Cola:\n{PIX_KEY}\n\n"
        "Após pagar, toque em **Confirmar pagamento**."
    )

    teclado = [
        [InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar")]
    ]

    await q.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= CONFIRMAR PAGAMENTO =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plano = pagamentos_pendentes.get(q.from_user.id)
    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente.")
        return

    teclado = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{q.from_user.id}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{q.from_user.id}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"💳 PAGAMENTO PENDENTE\n\n"
        f"👤 ID: {q.from_user.id}\n"
        f"📦 Plano: {plano['nome']}\n"
        f"💰 Valor: R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

    await q.message.reply_text("⏳ Pagamento enviado para aprovação.")

# ================= APROVAR / REJEITAR =================
async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    acao, uid = q.data.split("_")
    uid = int(uid)

    plano = pagamentos_pendentes.get(uid)
    if not plano:
        await q.message.reply_text("❌ Pedido não encontrado.")
        return

    if acao == "aprovar":
        link = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await context.bot.send_message(
            uid,
            f"✅ Pagamento aprovado!\n\n🔗 Acesso ao grupo:\n{link.invite_link}"
        )

        await q.message.reply_text("✅ Aprovado e link enviado.")
    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        await q.message.reply_text("❌ Rejeitado.")

    pagamentos_pendentes.pop(uid, None)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="confirmar"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))

    print("🤖 BOT ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()
