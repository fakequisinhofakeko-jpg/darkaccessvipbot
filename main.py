import os
import uuid
import asyncio
import requests
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

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
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await query.edit_message_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== CRIAR PIX ==================
def create_pix(plan_key, user_id):
    plan = PLANS[plan_key]

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": float(plan["price"]),
        "description": plan["name"],
        "payment_method_id": "pix",
        "external_reference": f"user_{user_id}_{plan_key}",
        "payer": {
            "email": f"user{user_id}@darkaccessvip.com"
        }
    }

    response = requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers=headers,
        json=data
    )

    result = response.json()

    if response.status_code not in (200, 201):
        print("❌ ERRO MERCADO PAGO:", result)

    return result

# ================== COMPRAR ==================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("buy_", "")
    plan = PLANS[plan_key]

    payment = create_pix(plan_key, query.from_user.id)

    try:
        pix_code = payment["point_of_interaction"]["transaction_data"]["qr_code"]
        payment_id = payment["id"]
    except Exception:
        await query.edit_message_text(
            "❌ *Erro ao gerar o PIX.*\nTente novamente.",
            parse_mode="Markdown"
        )
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    keyboard = [[InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]]

    await query.edit_message_text(
        f"💳 *Pagamento PIX*\n\n"
        f"📌 Plano: {plan['name']}\n"
        f"💰 Valor: R${plan['price']}\n\n"
        f"🔑 *Pix Copia e Cola:*\n"
        f"`{pix_code}`\n\n"
        f"Após pagar, clique em *Verificar pagamento*.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== VERIFICAR PAGAMENTO ==================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    if not payment_id:
        await query.edit_message_text("❌ Nenhum pagamento encontrado.")
        return

    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    ).json()

    if response.get("status") == "approved":
        plan = PLANS[plan_key]

        # calcula expiração
        expires_at = (
            datetime.now() + timedelta(days=plan["days"])
            if plan["days"] else None
        )

        # salva usuário
        context.application.bot_data.setdefault("users", {})
        context.application.bot_data["users"][query.from_user.id] = {
            "expires": expires_at
        }

        invite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await query.edit_message_text(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Entre no grupo VIP:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "⏳ Pagamento ainda não aprovado.\nTente novamente."
        )

# ================== EXPIRAÇÃO AUTOMÁTICA ==================
async def expiration_checker(app):
    while True:
        await asyncio.sleep(300)  # 5 minutos
        now = datetime.now()

        users = app.bot_data.get("users", {})
        for user_id, data in list(users.items()):
            expires = data["expires"]
            if expires and now >= expires:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, user_id)
                    await app.bot.unban_chat_member(GROUP_ID, user_id)
                    del users[user_id]
                except Exception as e:
                    print("Erro ao remover usuário:", e)

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))

    app.create_task(expiration_checker(app))

    app.run_polling()

if __name__ == "__main__":
    main()
