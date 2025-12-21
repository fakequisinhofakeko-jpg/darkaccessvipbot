import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = "SEU_TOKEN_AQUI"
ADMIN_ID = 123456789
GROUP_ID = -100XXXXXXXXXX

PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

PLANOS = {
    "vip1": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip3": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}  # user_id -> {"expira": datetime, "avisado": False}
mensagens_para_apagar = {}  # user_id -> [message_id]
logs = []
total_arrecadado = 0.0

logging.basicConfig(level=logging.INFO)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔞 **AVISO LEGAL**\n"
        "Conteúdo adulto +18 (anime)\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "📌 Pagamento via PIX\n"
        "🔒 Conteúdo premium"
    )

    keyboard = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="plano_vip3")]
    ]

    sent = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    mensagens_para_apagar.setdefault(update.effective_user.id, []).append(sent.message_id)

# ================= PLANOS =================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plano_id = query.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    pagamentos_pendentes[query.from_user.id] = plano

    texto = (
        f"📌 **Plano:** {plano['nome']}\n"
        f"💰 **Valor:** R${plano['valor']}\n\n"
        f"🔑 **PIX Copia e Cola:**\n`{PIX_KEY}`\n\n"
        "📷 Envie o comprovante e toque em **Confirmar pagamento**"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar_pagamento")]
    ]

    sent = await query.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    mensagens_para_apagar.setdefault(query.from_user.id, []).append(sent.message_id)

# ================= CONFIRMAR =================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    plano = pagamentos_pendentes.get(user_id)

    if not plano:
        await query.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user_id}"),
            InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{user_id}")
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"💳 **Pagamento pendente**\n"
            f"👤 ID: {user_id}\n"
            f"📦 Plano: {plano['nome']}\n"
            f"💰 Valor: R${plano['valor']}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    await query.message.reply_text("⏳ Pagamento enviado para aprovação.")

# ================= APROVAR / REJEITAR =================
async def moderar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao, user_id = query.data.split("_")
    user_id = int(user_id)

    plano = pagamentos_pendentes.get(user_id)
    if not plano:
        await query.message.reply_text("❌ Pedido não encontrado.")
        return

    if acao == "aprovar":
        expira = datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[user_id] = {"expira": expira, "avisado": False}

        global total_arrecadado
        total_arrecadado += plano["valor"]

        link = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            expire_date=int((datetime.now() + timedelta(minutes=30)).timestamp()),
            member_limit=1
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Pagamento aprovado!\n🔗 Acesso ao grupo:\n{link.invite_link}"
        )

        logs.append(f"{user_id} aprovado {plano['nome']}")
        del pagamentos_pendentes[user_id]

        await query.message.reply_text("✅ Pagamento aprovado.")

    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Pagamento rejeitado. Fale com o suporte."
        )
        del pagamentos_pendentes[user_id]
        await query.message.reply_text("❌ Pagamento rejeitado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texto = (
        f"👑 **Painel Admin**\n\n"
        f"👥 Usuários ativos: {len(usuarios_ativos)}\n"
        f"💰 Total arrecadado: R${total_arrecadado:.2f}"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")

# ================= JOBS =================
async def verificar_expiracoes(context: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now()

    for user_id, dados in list(usuarios_ativos.items()):
        if agora >= dados["expira"]:
            await context.bot.ban_chat_member(GROUP_ID, user_id)
            del usuarios_ativos[user_id]

        elif not dados["avisado"] and dados["expira"] - agora <= timedelta(days=3):
            await context.bot.send_message(
                chat_id=user_id,
                text="⏰ Seu acesso VIP vence em 3 dias."
            )
            dados["avisado"] = True

async def limpar_mensagens(context: ContextTypes.DEFAULT_TYPE):
    for user_id, msgs in mensagens_para_apagar.items():
        for msg_id in msgs:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                pass
        mensagens_para_apagar[user_id] = []

# ================= MAIN =================
async def post_init(app):
    app.job_queue.run_repeating(verificar_expiracoes, interval=3600)
    app.job_queue.run_repeating(limpar_mensagens, interval=1800)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="confirmar_pagamento"))
    app.add_handler(CallbackQueryHandler(moderar_pagamento, pattern="^(aprovar|rejeitar)_"))

    app.run_polling()

if __name__ == "__main__":
    main()
