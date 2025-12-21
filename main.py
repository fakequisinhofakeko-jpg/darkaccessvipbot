import os
import json
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================
# CONFIGURAÇÕES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
ARQUIVO_PAGAMENTOS = "pagamentos.json"

# =========================
# UTILIDADES
# =========================
def carregar_pagamentos():
    if not os.path.exists(ARQUIVO_PAGAMENTOS):
        return {}
    with open(ARQUIVO_PAGAMENTOS, "r") as f:
        return json.load(f)

def salvar_pagamentos(dados):
    with open(ARQUIVO_PAGAMENTOS, "w") as f:
        json.dump(dados, f, indent=4)

# =========================
# START / MENU
# =========================
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
# PIX MERCADO PAGO
# =========================
def criar_pix(valor, descricao):
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": float(valor),
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

# =========================
# CALLBACK PLANOS
# =========================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    planos = {
        "vip_1m": (24.90, "VIP 1 Mês"),
        "vip_3m": (64.90, "VIP 3 Meses"),
        "vip_vitalicio": (149.90, "VIP Vitalício")
    }

    valor, plano = planos[query.data]
    pagamento = criar_pix(valor, plano)

    try:
        pix = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]

        pagamentos = carregar_pagamentos()
        pagamentos[str(query.from_user.id)] = {
            "plano": plano,
            "valor": valor,
            "status": "pendente"
        }
        salvar_pagamentos(pagamentos)

        teclado = [[InlineKeyboardButton("✅ Já paguei", callback_data="ja_paguei")]]

        await query.message.reply_text(
            f"💳 *Pagamento PIX*\n\n"
            f"📌 Plano: {plano}\n"
            f"💰 Valor: R${valor}\n\n"
            f"`{pix}`\n\n"
            f"Após pagar, clique em *Já paguei*.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(teclado)
        )
    except:
        await query.message.reply_text("❌ Erro ao gerar PIX.")

# =========================
# CONFIRMAÇÃO MANUAL
# =========================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pagamentos = carregar_pagamentos()
    user_id = str(query.from_user.id)

    if user_id in pagamentos:
        pagamentos[user_id]["status"] = "em verificação"
        salvar_pagamentos(pagamentos)

        await query.message.reply_text(
            "⏳ Pagamento marcado como *EM VERIFICAÇÃO*.\n"
            "A liberação automática será ativada em breve.",
            parse_mode="Markdown"
        )

# =========================
# /status
# =========================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    pagamentos = carregar_pagamentos()

    if user_id not in pagamentos:
        await update.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    info = pagamentos[user_id]
    await update.message.reply_text(
        f"📄 *Status do pagamento*\n\n"
        f"📌 Plano: {info['plano']}\n"
        f"💰 Valor: R${info['valor']}\n"
        f"⏳ Status: *{info['status'].upper()}*",
        parse_mode="Markdown"
    )

# =========================
# MENU CALLBACK
# =========================
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_planos":
        await mostrar_planos(update, context)

    elif query.data == "menu_ajuda":
        await query.message.reply_text(
            "❓ *Ajuda*\n\n"
            "1️⃣ Escolha um plano\n"
            "2️⃣ Gere o PIX\n"
            "3️⃣ Clique em Já paguei\n"
            "4️⃣ Acompanhe com /status",
            parse_mode="Markdown"
        )

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(callback_planos, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="^ja_paguei$"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
