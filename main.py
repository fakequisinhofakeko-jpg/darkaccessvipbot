import os
import asyncio
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

import mercadopago

# =========================
# VARIÁVEIS DE AMBIENTE
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# =========================
# MERCADO PAGO
# =========================
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# =========================
# DADOS EM MEMÓRIA
# =========================
pagamentos = {}

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot online com sucesso!\n\n"
        "Use /planos para ver os planos disponíveis."
    )

# =========================
# PLANOS
# =========================
async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 VIP 1 Mês - R$24,90", callback_data="vip_1m")]
    ]

    await update.message.reply_text(
        "📌 Escolha seu plano:",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# =========================
# GERAR PIX
# =========================
async def callback_planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    pagamento = mp.payment().create({
        "transaction_amount": 24.90,
        "description": "VIP 1 Mês",
        "payment_method_id": "pix",
        "payer": {
            "email": f"user{user_id}@telegram.com"
        }
    })

    pix = pagamento["response"]["point_of_interaction"]["transaction_data"]

    pagamentos[user_id] = {
        "payment_id": pagamento["response"]["id"],
        "plano": "VIP 1 Mês",
        "status": "pending",
        "expira_em": None
    }

    await query.message.reply_text(
        f"💠 *Pagamento via PIX*\n\n"
        f"🔢 *Copia e Cola:*\n`{pix['qr_code']}`\n\n"
        "⏳ Após pagar, aguarde a confirmação automática.",
        parse_mode="Markdown"
    )

# =========================
# VERIFICADOR DE PAGAMENTO
# =========================
async def verificador_pagamento(app):
    while True:
        await asyncio.sleep(30)

        for user_id, info in list(pagamentos.items()):
            if info["status"] != "pending":
                continue

            payment_id = info["payment_id"]
            status = mp.payment().get(payment_id)["response"]["status"]

            if status == "approved":
                expira = datetime.now() + timedelta(days=30)

                pagamentos[user_id]["status"] = "approved"
                pagamentos[user_id]["expira_em"] = expira

                await app.bot.send_message(
                    chat_id=user_id,
                    text="✅ Pagamento aprovado!\nVocê foi liberado no grupo VIP."
                )

                try:
                    await app.bot.unban_chat_member(GROUP_ID, user_id)
                    await app.bot.invite_chat_member(GROUP_ID, user_id)
                except:
                    pass

# =========================
# VERIFICADOR DE EXPIRAÇÃO
# =========================
async def verificador_expiracao(app):
    while True:
        await asyncio.sleep(60)

        agora = datetime.now()

        for user_id, info in list(pagamentos.items()):
            expira = info.get("expira_em")

            if expira and agora > expira:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, user_id)
                    await app.bot.unban_chat_member(GROUP_ID, user_id)

                    await app.bot.send_message(
                        chat_id=user_id,
                        text="⛔ Seu acesso VIP expirou.\nRenove para continuar."
                    )

                    del pagamentos[user_id]

                except:
                    pass

# =========================
# MAIN
# =========================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("planos", planos))
    app.add_handler(CallbackQueryHandler(callback_planos))

    app.create_task(verificador_pagamento(app))
    app.create_task(verificador_expiracao(app))

    print("Bot iniciado")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
