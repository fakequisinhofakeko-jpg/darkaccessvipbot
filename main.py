import os
import uuid
import asyncio
import requests
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== VARIÁVEIS ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ================== PLANOS ==================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90, "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90, "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90, "days": None},
}

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📌 Ver planos", callback_data="plans")]]
    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== PLANOS ==================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="vip_vitalicio")]
    ]

    await q.edit_message_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== PIX ==================
def criar_pix(plan_key, user_id):
    plan = PLANS[plan_key]

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": plan["price"],
        "description": plan["name"],
        "payment_method_id": "pix",
        "payer": {"email": f"user{user_id}@vip.com"}
    }

    r = requests.post("https://api.mercadopago.com/v1/payments", json=data, headers=headers)
    return r.json()

# ================== LINK CARTÃO ==================
def criar_link_cartao(plan_key):
    plan = PLANS[plan_key]

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "items": [{
            "title": plan["name"],
            "quantity": 1,
            "unit_price": plan["price"]
        }],
        "back_urls": {
            "success": "https://t.me/seu_bot",
            "failure": "https://t.me/seu_bot"
        },
        "auto_return": "approved"
    }

    r = requests.post("https://api.mercadopago.com/checkout/preferences", json=data, headers=headers)
    return r.json()["init_point"]

# ================== ESCOLHA PAGAMENTO ==================
async def escolher_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data
    context.user_data["plan"] = plan_key

    pix = criar_pix(plan_key, q.from_user.id)
    pix_code = pix["point_of_interaction"]["transaction_data"]["qr_code"]
    payment_id = pix["id"]

    context.user_data["payment_id"] = payment_id

    link_cartao = criar_link_cartao(plan_key)

    keyboard = [
        [InlineKeyboardButton("💳 Pagar com Cartão", url=link_cartao)],
        [InlineKeyboardButton("🔄 Verificar PIX", callback_data="check_pix")]
    ]

    await q.edit_message_text(
        f"💰 *{PLANS[plan_key]['name']}*\n"
        f"💵 R$ {PLANS[plan_key]['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{pix_code}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== VERIFICAR PIX ==================
async def check_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    r = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    ).json()

    if r.get("status") == "approved":
        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)
        await q.edit_message_text(
            f"✅ *Pagamento aprovado!*\n\n🔓 Acesse o grupo:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(escolher_pagamento, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(check_pix, pattern="^check_pix$"))

    app.run_polling()

if __name__ == "__main__":
    main()
