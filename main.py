from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================
BOT_TOKEN = "COLE_SEU_TOKEN_AQUI"
ADMIN_ID = 123456789              # SEU ID
GROUP_ID = -1003513694224         # SEU GRUPO
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}
avisos_enviados = set()
logs = []
total_arrecadado = 0.0

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🔞 **AVISO LEGAL**\n"
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
        f"📦 **Plano:** {plano['nome']}\n"
        f"💰 **Valor:** R${plano['valor']}\n\n"
        f"🔑 **PIX Copia e Cola:**\n`{PIX_KEY}`\n\n"
        "Após pagar, toque em **Confirmar pagamento**"
    )

    teclado = [
        [InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar_pagamento")]
    ]

    await q.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= CONFIRMAR =================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    plano = pagamentos_pendentes.get(user_id)

    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente.")
        return

    teclado = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user_id}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{user_id}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"💳 **Pagamento pendente**\n"
        f"👤 ID: {user_id}\n"
        f"📦 {plano['nome']}\n"
        f"💰 R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

    await q.message.reply_text("⏳ Enviado para aprovação.")

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
        expira = datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = expira

        global total_arrecadado
        total_arrecadado += plano["valor"]
        logs.append((uid, plano["nome"], plano["valor"], datetime.now()))

        convite = await context.bot.create_chat_invite_link(
            GROUP_ID,
            member_limit=1
        )

        await context.bot.send_message(
            uid,
            f"✅ Pagamento aprovado!\n\n🔗 Acesso:\n{convite.invite_link}"
        )

        del pagamentos_pendentes[uid]
        await q.message.reply_text("✅ Aprovado.")

    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        del pagamentos_pendentes[uid]
        await q.message.reply_text("❌ Rejeitado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texto = (
        f"👑 **Painel Admin**\n\n"
        f"👥 Usuários ativos: {len(usuarios_ativos)}\n"
        f"💳 Pendentes: {len(pagamentos_pendentes)}\n"
        f"💰 Total: R${total_arrecadado:.2f}"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")

# ================= EXPIRAÇÃO + AVISO =================
async def verificar_expiracoes(context: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now()

    for uid, expira in list(usuarios_ativos.items()):
        dias = (expira - agora).days

        if dias == 3 and uid not in avisos_enviados:
            await context.bot.send_message(
                uid,
                "⏰ Seu acesso VIP vence em 3 dias."
            )
            avisos_enviados.add(uid)

        if agora >= expira:
            await context.bot.ban_chat_member(GROUP_ID, uid)
            await context.bot.unban_chat_member(GROUP_ID, uid)
            del usuarios_ativos[uid]

# ================= RELATÓRIO DIÁRIO =================
async def relatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    texto = (
        f"📊 **Relatório Diário**\n\n"
        f"💳 Pendentes: {len(pagamentos_pendentes)}\n"
        f"👥 Ativos: {len(usuarios_ativos)}\n"
        f"💰 Total: R${total_arrecadado:.2f}"
    )

    await context.bot.send_message(ADMIN_ID, texto, parse_mode="Markdown")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="confirmar_pagamento"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))

    app.job_queue.run_repeating(verificar_expiracoes, interval=3600)
    app.job_queue.run_daily(relatorio_diario, time=datetime.strptime("09:00", "%H:%M").time())

    app.run_polling()

if __name__ == "__main__":
    main()
