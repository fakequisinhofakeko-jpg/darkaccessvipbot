import os
import time
import uuid
import requests
from flask import Flask, request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

payments = {}

# =====================
# CRIAR PIX
# =====================
def criar_pix(user_id, valor):
    payment_id = str(uuid.uuid4())

    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {MP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "transaction_amount": valor,
        "description": "Acesso VIP",
        "payment_method_id": "pix",
        "payer": {
            "email": f"user{user_id}@vipbot.com"
        }
    }

    r = requests.post(url, json=data, headers=headers).json()

    payments[r["id"]] = user_id

    return r["point_of_interaction"]["transaction_data"]["qr_code"]

# =====================
# WEBHOOK
# =====================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if data.get("type") == "payment":
        payment_id = data["data"]["id"]

        headers = {"Authorization": f"Bearer {MP_TOKEN}"}
        payment = requests.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers=headers
        ).json()

        if payment["status"] == "approved":
            user_id = payments.get(payment_id)

            if user_id:
                link = bot.create_chat_invite_link(
                    chat_id=GROUP_ID,
                    expire_date=int(time.time()) + 3600
                )

                bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Pagamento confirmado!\n\n🔗 Acesse o grupo:\n{link.invite_link}"
                )

    return "ok"

# =====================
# START
# =====================
@app.route("/")
def home():
    return "Bot ativo"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
