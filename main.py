from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================
BOT_TOKEN = 8444138111:AAFFkyvFRQMa0gyG77_pnyd7uWuR545gDkQ
ADMIN_ID = 123456789
GROUP_ID = -1003513694224
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}
avisos_3dias = set()
total_arrecadado = 0.0

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🔞 *AVISO LEGAL*\n"
        "Conteúdo adulto +18 (anime)\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "📌 Pagamento via PIX\n"
        "🔒 Conteúdo premium"
    )

    teclado = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="plano_vip3")],
    ]

    await update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= ESCOLHER PLANO =================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plano_id = q.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    pagamentos_pendentes[q.from_user.id] = plano

    texto = (
        f"📦 *Plano:* {plano['nome']}\n"
        f"💰 *Valor:* R${plano['valor']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{PIX_KEY}`\n\n"
        "Após pagar, clique em *Confirmar pagamento*"
    )

    teclado = [
        [InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar")]
    ]

    await q.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= CONFIRMAR =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    plano = pagamentos_pendentes.get(uid)

    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente.")
        return

    teclado = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{uid}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{uid}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"💳 *Pagamento pendente*\n"
        f"👤 ID: `{uid}`\n"
        f"📦 {plano['nome']}\n"
        f"💰 R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

    await q.message.reply_text("⏳ Enviado para aprovação.")

# ================= MODERAR =================
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
        global total_arrecadado
        total_arrecadado += plano["valor"]

        expira = datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = expira

        convite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await context.bot.send_message(
            uid,
            f"✅ Pagamento aprovado!\n\n🔗 Acesso ao grupo:\n{convite.invite_link}"
        )

        del pagamentos_pendentes[uid]
        await q.message.reply_text("✅ Aprovado.")

    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        del pagamentos_pendentes[uid]
        await q.message.reply_text("❌ Rejeitado.")

# ================= EXPIRAÇÃO + AVISO =================
async def verificar_expiracoes(context: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now()

    for uid, expira in list(usuarios_ativos.items()):
        dias = (expira - agora).days

        if dias == 3 and uid not in avisos_3dias:
            await context.bot.send_message(uid, "⏰ Seu VIP vence em 3 dias.")
            avisos_3dias.add(uid)

        if agora >= expira:
            await context.bot.ban_chat_member(GROUP_ID, uid)
            await context.bot.unban_chat_member(GROUP_ID, uid)
            del usuarios_ativos[uid]

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texto = (
        f"👑 *Painel Admin*\n\n"
        f"👥 Ativos: {len(usuarios_ativos)}\n"
        f"💳 Pendentes: {len(pagamentos_pendentes)}\n"
        f"💰 Total: R${total_arrecadado:.2f}"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="confirmar"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))

    app.job_queue.run_repeating(verificar_expiracoes, interval=3600)

    app.run_polling()

if __name__ == "__main__":
    main()
