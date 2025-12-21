import os
import json
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

VIP_GROUP_ID = -1003513694224
ARQUIVO_PAGAMENTOS = "pagamentos.json"

# =========================
# UTILIDADES JSON
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
# START
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
# GERAR PIX
# =========================
def criar_pix(valor, descricao):
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": valor,
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {
            "email": "cliente@telegram.com"
        }
    }

    response = requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers=headers,
        json=data
    )

    return response.json()

# =========================
# CALLBACK PLANOS (PIX + BOTÃO JÁ PAGUEI)
# =========================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "vip_1m":
        valor, plano = 24.90, "VIP 1 Mês"
    elif query.data == "vip_3m":
        valor, plano = 64.90, "VIP 3 Meses"
    elif query.data == "vip_vitalicio":
        valor, plano = 149.90, "VIP Vitalício"
    else:
        return

    pagamento = criar_pix(valor, plano)

    try:
        pix = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
        payment_id = pagamento["id"]

        pagamentos = carregar_pagamentos()
        pagamentos[str(query.from_user.id)] = {
            "plano": plano,
            "valor": valor,
            "payment_id": payment_id,
            "status": "pendente"
        }
        salvar_pagamentos(pagamentos)

        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Já paguei", callback_data="ja_paguei")]
        ])

        await query.message.reply_text(
            f"💳 *Pagamento PIX*\n\n"
            f"📌 Plano: {plano}\n"
            f"💰 Valor: R${valor}\n\n"
            f"`{pix}`\n\n"
            f"⏳ Status: *PENDENTE*",
            reply_markup=teclado,
            parse_mode="Markdown"
        )

    except Exception:
        await query.message.reply_text(
            f"❌ Erro ao gerar Pix.\n\n{pagamento}",
            parse_mode="Markdown"
        )

# =========================
# CALLBACK “JÁ PAGUEI”
# =========================
async def confirmar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    pagamentos = carregar_pagamentos()

    if user_id in pagamentos:
        pagamentos[user_id]["status"] = "em_verificacao"
        salvar_pagamentos(pagamentos)

        await query.message.reply_text(
            "🕒 Pagamento marcado como *EM VERIFICAÇÃO*.\n\n"
            "A liberação automática será ativada em breve.",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text(
            "⚠️ Nenhum pagamento encontrado para este usuário.",
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
            "ℹ️ *Ajuda*\n\n"
            "• Escolha um plano\n"
            "• Gere o Pix\n"
            "• Clique em *Já paguei*\n"
            "• Aguarde liberação automática",
            parse_mode="Markdown"
        )

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_planos, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(confirmar_pagamento, pattern="^ja_paguei$"))
    app.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot rodando com JSON + Etapa 1...")
    app.run_polling()

if __name__ == "__main__":
    main()
