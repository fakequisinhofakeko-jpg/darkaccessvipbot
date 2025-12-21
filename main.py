import os
import uuid
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Header
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
import threading
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
GRUPO_VIP_ID = -1003513694224

bot = Bot(BOT_TOKEN)
app = FastAPI()

# memória simples (etapa 5 vira banco)
pagamentos = {}

# ======================
# BOT START
# ======================
async def start(update, context):
    await update.message.reply_text(
        "🔥 Dark Access VIP\n\n"
        "Escolha um plano e pague.\n"
        "O acesso é liberado automaticamente."
    )

# ======================
# WEBHOOK MERCADO PAGO
# ======================
@app.post("/webhook")
async def mercado_pago_webhook(
    request: Request,
    x_signature: str = Header(None)
):
    data = await request.json()

    if x_signature != WEBHOOK_SECRET:
        return {"error": "unauthorized"}

    if data.get("type") != "payment":
        return {"status": "ignored"}

    payment_id = data["data"]["id"]

    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    payment = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers=headers
    ).json()

    if payment.get("status") != "approved":
        return {"status": "pending"}

    external_reference = payment.get("external_reference")
    if not external_reference:
        return {"error": "no user"}

    user_id = int(external_reference)

    link = await bot.create_chat_invite_link(
        chat_id=GRUPO_VIP_ID,
        member_limit=1
    )

    await bot.send_message(
        chat_id=user_id,
        text=(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Link de acesso:\n{link.invite_link}"
        ),
        parse_mode="Markdown"
    )

    return {"status": "ok"}

# ======================
# BOT + API JUNTOS
# ======================
def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.run_polling()

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_api()
