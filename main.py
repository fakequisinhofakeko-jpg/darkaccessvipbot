import os
import uuid
import requests
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

# =========================
# CONFIGURAÇÕES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# =========================
# START / MENU PRINCIPAL
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="menu_planos")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="menu_pagamento")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="menu_ajuda")]
    ]

    await update.message.reply_text(
        "🔥 *Bem-vindo ao Dark Access VIP*\n\n"
        "Escolha uma opção abaixo:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# =========================
# MENU PLANOS
# =========================
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

# =========================
# CRIAR PIX (MERCADO PAGO)
# =========================
def criar_pix(valor, descricao):
    url = "https://api.mercadopago.com/v1/payments"

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": float(valor),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {
            "email": "comprador@telegram.com"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        print("❌ ERRO MERCADO PAGO:", response.text)
        return None

    return response.json()

# =========================
# CALLBACK DOS PLANOS
# =========================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "vip_1m":
        valor = 24.90
        plano = "VIP 1 Mês"
    elif query.data == "vip_3m":
        valor = 64.90
        plano = "VIP 3 Meses"
    elif query.data == "vip_vitalicio":
        valor = 149.90
        plano = "VIP Vitalício"
    else:
        return

    pagamento = criar_pix(valor, plano)

    if not pagamento:
        await query.message.reply_text(
            "❌ *Erro ao gerar o Pix.*\n"
            "Pagamento não autorizado pelo Mercado Pago.",
            parse_mode="Markdown"
        )
        return

    pix_copia_cola = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]

    await query.message.reply_text(
        f"💳 *Pagamento PIX*\n\n"
        f"📌 Plano: {plano}\n"
        f"💰 Valor: R${valor}\n\n"
        f"🔑 *Pix Copia e Cola:*\n"
        f"`{pix_copia_cola}`\n\n"
        f"⚠️ Após pagar, aguarde a confirmação.",
        parse_mode="Markdown"
    )

# =========================
# CALLBACK MENU GERAL
# =========================
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_planos":
        await mostrar_planos(update, context)

    elif query.data == "menu_pagamento":
        await query.message.reply_text(
            "💳 Os pagamentos são feitos via *PIX automático*.\n"
            "Escolha um plano para gerar o Pix.",
            parse_mode="Markdown"
        )

    elif query.data == "menu_ajuda":
        await query.message.reply_text(
            "❓ *Ajuda*\n\n"
            "• Escolha um plano\n"
            "• Gere o Pix\n"
            "• Pague e aguarde a liberação\n\n"
            "Suporte automático.",
            parse_mode="Markdown"
        )

# =========================
# INICIALIZAÇÃO
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_planos, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
