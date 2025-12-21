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

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

mp = mercadopago.SDK(MP_ACCESS_TOKEN)

pagamentos = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot online com sucesso!\n\nUse /planos para comprar acesso VIP."
    )

# ================= PLANOS =================
async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 VIP 1 Mês - R$24,90", callback_data="vip_1m")]
    ]
    await update.message.reply_text(
        "📌 Escolha seu plano:",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= GERAR PIX =================
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
        "status": "pending",
        "expira_em": None
    }

    await query.message.reply_text(
        f"💠 *PIX GERADO*\n\n"
        f"`{pix['qr_code']}`\n\n"
        "⏳ Após o pagamento, o acesso será liberado automaticamente.",
        parse_mode="Markdown"
    )

# ================= VERIFICAR PAGAMENTO =================
async def verificador_pagamento(app):
    while True:
        await asyncio.sleep(30)

        for user_id, info in list(pagamentos.items()):
            if info["status"] != "pending":
                continue

            status = mp.payment().get(info["payment_id"])["response"]["status"]

            if status == "approved":
                expira = datetime.now() + timedelta(days=30)

                pagamentos[user_id]["status"] = "approved"
                pagamentos[user_id]["expira_em"] = expira

                link = await app.bot.create_chat_invite_link(
                    chat_id=GROUP_ID,
                    member_limit=1
                )

                await app.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "✅ *Pagamento aprovado!*\n\n"
                        "🔗 Entre no grupo VIP pelo link abaixo:\n"
                        f"{link.invite_link}\n\n"
                        f"⏳ Expira em: {expira.strftime('%d/%m/%Y')}"
                    ),
                    parse_mode="Markdown"
                )

# ================= VERIFICAR EXPIRAÇÃO =================
async def verificador_expiracao(app):
    while True:
        await asyncio.sleep(60)
        agora = datetime.now()

        for user_id, info in list(pagamentos.items()):
            if info["expira_em"] and agora > info["expira_em"]:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, user_id)
                    await app.bot.unban_chat_member(GROUP_ID, user_id)
                except:
                    pass

                await app.bot.send_message(
                    chat_id=user_id,
                    text="⛔ Seu acesso VIP expirou. Renove para continuar."
                )

                del pagamentos[user_id]

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("planos", planos))
    app.add_handler(CallbackQueryHandler(callback_planos))

    app.create_task(verificador_pagamento(app))
    app.create_task(verificador_expiracao(app))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
