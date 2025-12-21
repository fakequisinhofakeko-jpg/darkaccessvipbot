import os
import asyncio
import threading
from datetime import datetime, timedelta

from flask import Flask
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

import mercadopago

# =========================
# VARIÁVEIS DE AMBIENTE
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not BOT_TOKEN or not GROUP_ID or not MP_ACCESS_TOKEN:
    raise Exception("❌ Variáveis de ambiente não configuradas")

# =========================
# MERCADO PAGO
# =========================
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# =========================
# FLASK (KEEP ALIVE - RAILWAY)
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================
# MEMÓRIA SIMPLES
# =========================
pagamentos = {}

PLANOS = {
    "vip_1m": {"nome": "VIP 1 Mês", "valor": 24.90, "dias": 30},
    "vip_3m": {"nome": "VIP 3 Meses", "valor": 64.90, "dias": 90},
    "vip_vitalicio": {"nome": "VIP Vitalício", "valor": 149.90, "dias": 36500}
}

# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]
    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📌 *Ajuda*\n\n"
        "• Escolha um plano\n"
        "• Pague o Pix\n"
        "• A liberação é automática\n\n"
        "Use /status para acompanhar",
        parse_mode="Markdown"
    )

async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
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
# CRIAR PAGAMENTO PIX
# =========================
async def criar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plano = PLANOS.get(query.data)
    user_id = query.from_user.id

    pagamento = mp.payment().create({
        "transaction_amount": plano["valor"],
        "description": plano["nome"],
        "payment_method_id": "pix",
        "payer": {
            "email": f"user{user_id}@telegram.com"
        }
    })

    pagamento_id = pagamento["response"]["id"]
    qr = pagamento["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
    qr_base64 = pagamento["response"]["point_of_interaction"]["transaction_data"]["qr_code_base64"]

    pagamentos[user_id] = {
        "id": pagamento_id,
        "plano": plano,
        "status": "pending"
    }

    await query.message.reply_text(
        f"💳 *Pagamento Pix gerado*\n\n"
        f"📌 Plano: {plano['nome']}\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"⚠️ Após pagar, a liberação é automática.\n"
        f"Use /status para acompanhar.",
        parse_mode="Markdown"
    )

# =========================
# STATUS + LIBERAÇÃO AUTOMÁTICA
# =========================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in pagamentos:
        await update.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    pagamento = pagamentos[user_id]
    mp_status = mp.payment().get(pagamento["id"])["response"]["status"]

    if mp_status == "approved":
        if pagamento["status"] != "approved":
            pagamento["status"] = "approved"
            expira = datetime.now() + timedelta(days=pagamento["plano"]["dias"])

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"✅ Novo membro liberado: {update.message.from_user.first_name}"
            )

        await update.message.reply_text(
            f"✅ *Pagamento aprovado!*\n"
            f"Plano: {pagamento['plano']['nome']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"⏳ *Pagamento ainda não aprovado*\n"
            f"Status: {mp_status}",
            parse_mode="Markdown"
        )

# =========================
# BOT
# =========================
async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CallbackQueryHandler(planos, pattern="planos"))
    app_bot.add_handler(CallbackQueryHandler(ajuda, pattern="ajuda"))
    app_bot.add_handler(CallbackQueryHandler(criar_pagamento, pattern="vip_"))

    print("🤖 Bot iniciado")
    await app_bot.run_polling()

# =========================
# START FINAL (ANTI-CRASH)
# =========================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    asyncio.run(main())
