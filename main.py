from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from datetime import datetime, timedelta
import time

# ================= CONFIG =================
BOT_TOKEN = "SEU_TOKEN_AQUI"
ADMIN_ID = 1208316553
GROUP_ID = -1003513694224
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

# ================= PLANOS =================
PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
    "vip_vitalicio": {"nome": "VIP Vitalício", "valor": 149.90, "dias": None},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}          # controle de plano ativo
confirmacoes_enviadas = set() # anti-spam
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

    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(teclado))

# ================= ESCOLHER PLANO =================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    plano_id = q.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    # 🔒 BLOQUEIO DE PLANO ATIVO
    ativo = usuarios_ativos.get(user_id)
    if ativo:
        if ativo["plano"] == plano_id:
            if ativo["expira_em"] is None or ativo["expira_em"] > datetime.now():
                await q.message.reply_text(
                    "⚠️ Você já possui esse plano ativo.\n"
                    "Aguarde o vencimento para comprar novamente."
                )
                return

    pagamentos_pendentes[user_id] = plano | {"id": plano_id}

    texto = (
        f"📦 {plano['nome']}\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"🔑 PIX Copia e Cola:\n{PIX_KEY}\n\n"
        "Após pagar, toque em **Confirmar pagamento**."
    )

    teclado = [[InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar")]]

    await q.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(teclado), parse_mode="Markdown")

# ================= CONFIRMAR PAGAMENTO =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    # 🛑 ANTI-SPAM
    if user_id in confirmacoes_enviadas:
        return

    plano = pagamentos_pendentes.get(user_id)
    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente encontrado.")
        return

    confirmacoes_enviadas.add(user_id)

    await q.message.reply_text(
        "⏳ Pagamento enviado para aprovação.\n"
        "Assim que for confirmado, o acesso será liberado."
    )

    teclado_admin = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user_id}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{user_id}")
    ]]

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
        # ⏳ EXPIRAÇÃO DO LINK (10 min)
        link = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
            expire_date=int(time.time()) + 600
        )

        # 📅 REGISTRA PLANO ATIVO
        if plano["dias"]:
            expira = datetime.now() + timedelta(days=plano["dias"])
        else:
            expira = None  # vitalício

        usuarios_ativos[uid] = {
            "plano": plano["id"],
            "expira_em": expira
        }

        total_arrecadado += plano["valor"]

        await context.bot.send_message(
            uid,
            f"✅ Pagamento aprovado!\n\n"
            f"🔗 Acesso ao grupo (válido por 10 min):\n{link.invite_link}"
        )

        await q.message.reply_text("✅ Aprovado e link enviado.")
    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        await q.message.reply_text("❌ Rejeitado.")

    pagamentos_pendentes.pop(uid, None)
    confirmacoes_enviadas.discard(uid)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))

    app.run_polling()

if __name__ == "__main__":
    main()
