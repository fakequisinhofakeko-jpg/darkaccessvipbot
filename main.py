from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "8444138111:AAGuhgOzBtMsrNRQ1Zj2_pKuquMXi7jcHGo"
ADMIN_ID = 1208316553
GROUP_ID = -1003513694224
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90},
    "vip_vitalicio": {"nome": "VIP Vitalício", "valor": 149.90},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = set()
total_arrecadado = 0.0

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

    global total_arrecadado

    if acao == "aprovar":
        
# ================= CONFIRMAR PAGAMENTO =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    plano = pagamentos_pendentes.get(user_id)

    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente encontrado.")
        return

    # 👤 MENSAGEM PARA O COMPRADOR (SEM APROVAR / REJEITAR)
    await q.message.reply_text(
        "⏳ Pagamento enviado para aprovação.\n"
        "Assim que for confirmado, o acesso será liberado."
    )

    # 👑 BOTÕES EXCLUSIVOS DO ADMIN
    teclado_admin = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user_id}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{user_id}")
    ]]

    # 👑 MENSAGEM SOMENTE PARA O ADMIN
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "💳 PAGAMENTO PENDENTE\n\n"
            f"👤 ID: {user_id}\n"
            f"📦 Plano: {plano['nome']}\n"
            f"💰 Valor: R${plano['valor']}"
        ),
        reply_markup=InlineKeyboardMarkup(teclado_admin)
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    teclado = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="admin_usuarios")],
        [InlineKeyboardButton("⏳ Pagamentos pendentes", callback_data="admin_pendentes")],
        [InlineKeyboardButton("✅ Pagamentos aprovados", callback_data="admin_aprovados")],
        [InlineKeyboardButton("💰 Total arrecadado", callback_data="admin_total")],
    ]

    await update.message.reply_text(
        "👑 Painel Admin",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= CALLBACKS ADMIN =================
async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "admin_usuarios":
        texto = f"👥 Usuários ativos: {len(usuarios_ativos)}"
    elif q.data == "admin_pendentes":
        texto = f"⏳ Pagamentos pendentes: {len(pagamentos_pendentes)}"
    elif q.data == "admin_aprovados":
        texto = f"✅ Pagamentos aprovados: {len(usuarios_ativos)}"
    elif q.data == "admin_total":
        texto = f"💰 Total arrecadado: R${total_arrecadado:.2f}"
    else:
        texto = "❌ Opção inválida."

    await q.message.reply_text(texto)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))

    app.run_polling()

if __name__ == "__main__":
    main()
