import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90},
}

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📌 Planos", callback_data="plans")]
    ]
    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------- PLANOS ----------
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💎 1 Mês - R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 3 Meses - R$64,90", callback_data="buy_vip_3")]
    ]

    await query.edit_message_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------- CRIAR PIX ----------
def create_pix(plan_key, user_id):
    plan = PLANS[plan_key]

    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "transaction_amount": plan["price"],
        "description": plan["name"],
        "payment_method_id": "pix",
        "payer": {"email": f"user{user_id}@bot.com"}
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

# ---------- COMPRAR ----------
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("buy_", "")
    payment = create_pix(plan_key, query.from_user.id)

    pix_code = payment["point_of_interaction"]["transaction_data"]["qr_code"]
    payment_id = payment["id"]

    context.user_data["payment_id"] = payment_id

    keyboard = [
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]
    ]

    await query.edit_message_text(
        f"💳 *Pagamento PIX*\n\n"
        f"📌 Plano: {PLANS[plan_key]['name']}\n"
        f"💰 Valor: R${PLANS[plan_key]['price']}\n\n"
        f"🔑 *Copie o código PIX abaixo:*\n`{pix_code}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------- VERIFICAR PAGAMENTO ----------
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = context.user_data.get("payment_id")
    if not payment_id:
        await query.edit_message_text("❌ Nenhum pagamento encontrado.")
        return

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers).json()

    status = response.get("status")

    if status == "approved":
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"✅ Novo membro aprovado: @{query.from_user.username or query.from_user.id}"
        )
        await query.edit_message_text(
            "✅ *Pagamento aprovado!*\n\nAcesso liberado.",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "⏳ Pagamento ainda não aprovado.\nTente novamente em alguns segundos."
        )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="plans"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="check_payment"))

    app.run_polling()

if __name__ == "__main__":
    main()
