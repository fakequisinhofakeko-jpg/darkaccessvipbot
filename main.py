import os
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ======================
# CONFIGURAÇÕES
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

GRUPO_VIP_ID = -1003513694224

pagamentos = {}  # user_id -> dados do pagamento

# ======================
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="menu_planos")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="menu_ajuda")]
    ]

    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ======================
# PLANOS
# ======================
async def mostrar_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês - R$24,90", callback_data="vip_1m")],
        [InlineKeyboardButton("🔥 3 Meses - R$64,90", callback_data="vip_3m")],
        [InlineKeyboardButton("👑 Vitalício - R$149,90", callback_data="vip_vitalicio")]
    ]

    await update.callback_query.message.reply_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ======================
# CRIAR PIX
# ======================
def criar_pix(valor, descricao):
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "X-Idempotency-Key": str(uuid.uuid4()),
        "Content-Type": "application/json"
    }

    data = {
        "transaction_amount": valor,
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": "cliente@telegram.com"}
    }

    r = requests.post(
        "https://api.mercadopago.com/v1/payments",
        json=data,
        headers=headers
    )

    return r.json()

# ======================
# CALLBACK PLANOS
# ======================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    planos = {
        "vip_1m": (24.90, "VIP 1 Mês"),
        "vip_3m": (64.90, "VIP 3 Meses"),
        "vip_vitalicio": (149.90, "VIP Vitalício")
    }

    valor, nome = planos[query.data]
    pagamento = criar_pix(valor, nome)

    user_id = query.from_user.id

    pagamentos[user_id] = {
        "plano": nome,
        "valor": valor,
        "status": "EM VERIFICAÇÃO"
    }

    pix = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]

    teclado = [
        [InlineKeyboardButton("✅ Já paguei", callback_data="confirmar_pagamento")]
    ]

    await query.message.reply_text(
        f"💳 *Pagamento PIX*\n\n"
        f"📌 Plano: {nome}\n"
        f"💰 Valor: R${valor}\n\n"
        f"`{pix}`",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ======================
# CONFIRMAR PAGAMENTO
# ======================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    pagamento = pagamentos.get(user_id)

    if not pagamento:
        await query.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    # SIMULA aprovação (para testes)
    pagamento["status"] = "APROVADO"

    # cria link do grupo VIP
    link = await context.bot.create_chat_invite_link(
        chat_id=GRUPO_VIP_ID,
        member_limit=1
    )

    await query.message.reply_text(
        f"✅ *Pagamento aprovado!*\n\n"
        f"🔓 Acesse o grupo VIP pelo link abaixo:\n\n"
        f"{link.invite_link}",
        parse_mode="Markdown"
    )

# ======================
# STATUS
# ======================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pagamento = pagamentos.get(user_id)

    if not pagamento:
        await update.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    await update.message.reply_text(
        f"📄 *Status do pagamento*\n\n"
        f"📌 Plano: {pagamento['plano']}\n"
        f"💰 Valor: R${pagamento['valor']}\n"
        f"⏳ Status: {pagamento['status']}",
        parse_mode="Markdown"
    )

# ======================
# MENU CALLBACK
# ======================
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_planos":
        await mostrar_planos(update, context)

    elif query.data == "menu_ajuda":
        await query.message.reply_text(
            "❓ *Ajuda*\n\n"
            "• Escolha um plano\n"
            "• Gere o PIX\n"
            "• Confirme o pagamento\n"
            "• Receba o acesso automático",
            parse_mode="Markdown"
        )

# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(callback_planos, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="confirmar_pagamento"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
