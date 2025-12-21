import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

VIP_GROUP_ID = -1003513694224

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")]
    ]

    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha um plano:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# =========================
# PLANOS
# =========================
async def mostrar_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês – R$24,90", callback_data="vip_1")],
        [InlineKeyboardButton("🔥 3 Meses – R$64,90", callback_data="vip_3")],
        [InlineKeyboardButton("👑 Vitalício – R$149,90", callback_data="vip_v")]
    ]

    await update.callback_query.message.reply_text(
        "📌 Escolha seu plano:",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# =========================
# CRIAR PIX
# =========================
def criar_pix(valor, descricao):
    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": descricao
    }

    data = {
        "transaction_amount": valor,
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": "cliente@telegram.com"}
    }

    return requests.post(url, json=data, headers=headers).json()

# =========================
# VERIFICAR PAGAMENTO
# =========================
def verificar_pagamento(payment_id):
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    return requests.get(url, headers=headers).json()

# =========================
# CALLBACK PLANOS
# =========================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    planos = {
        "vip_1": (24.90, "VIP 1 Mês"),
        "vip_3": (64.90, "VIP 3 Meses"),
        "vip_v": (149.90, "VIP Vitalício")
    }

    valor, nome = planos[query.data]

    pagamento = criar_pix(valor, nome)
    payment_id = pagamento["id"]

    context.user_data["payment_id"] = payment_id

    pix = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]

    teclado = [
        [InlineKeyboardButton("✅ Já paguei", callback_data="confirmar_pagamento")]
    ]

    await query.message.reply_text(
        f"💳 *Pagamento PIX*\n\n"
        f"Plano: {nome}\n"
        f"Valor: R${valor}\n\n"
        f"`{pix}`",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# =========================
# CONFIRMAR PAGAMENTO
# =========================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = context.user_data.get("payment_id")

    if not payment_id:
        await query.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    status = verificar_pagamento(payment_id)["status"]

    if status == "approved":
        invite = await context.bot.create_chat_invite_link(
            chat_id=VIP_GROUP_ID,
            member_limit=1
        )

        await query.message.reply_text(
            f"✅ *Pagamento aprovado!*\n\n"
            f"🔗 Link VIP:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text(
            f"⏳ Pagamento ainda não aprovado.\nStatus: {status}"
        )

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mostrar_planos, pattern="planos"))
    app.add_handler(CallbackQueryHandler(callback_planos, pattern="vip_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="confirmar_pagamento"))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
