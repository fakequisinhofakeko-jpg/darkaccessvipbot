import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # variável do Railway
ADMIN_ID = 123456789                # SEU ID
GROUP_ID = -1003513694224           # SEU GRUPO
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}
total_arrecadado = 0.0

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🔞 **AVISO LEGAL**\n"
        "Conteúdo adulto +18 (anime).\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "💳 Pagamento via PIX\n"
        "🔒 Conteúdo VIP"
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

# ================= CONFIRMAR PAGAMENTO =================
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
        (
            f"💳 **Pagamento pendente**\n"
            f"👤 ID: `{user_id}`\n"
            f"📦 Plano: {plano['nome']}\n"
            f"💰 Valor: R${plano['valor']}"
        ),
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

    await q.message.reply_text("⏳ Pagamento enviado para aprovação.")

# ================= APROVAR / REJEITAR =================
async def moderar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    acao, uid = q.data.split("_")
    uid = int(uid)
    plano = pagamentos_pendentes.get(uid)

    if not plano:
        await q.message.reply_text("❌ Pedido não encontrado.")
        return

    global total_arrecadado

    if acao == "aprovar":
        expira = datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = expira
        total_arrecadado += plano["valor"]

        convite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await context.bot.send_message(
            uid,
            f"✅ **Pagamento aprovado!**\n\n🔗 Acesso ao grupo:\n{convite.invite_link}",
            parse_mode="Markdown"
        )

        del pagamentos_pendentes[uid]
        await q.message.reply_text("✅ Pagamento aprovado.")

    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        del pagamentos_pendentes[uid]
        await q.message.reply_text("❌ Pagamento rejeitado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texto = (
        "👑 **Painel Admin**\n\n"
        f"👥 Usuários ativos: {len(usuarios_ativos)}\n"
        f"💳 Pagamentos pendentes: {len(pagamentos_pendentes)}\n"
        f"💰 Total arrecadado: R${total_arrecadado:.2f}"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")

# ================= MAIN =================
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não definido no Railway")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="confirmar_pagamento"))
    app.add_handler(CallbackQueryHandler(moderar_pagamento, pattern="^(aprovar|rejeitar)_"))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
