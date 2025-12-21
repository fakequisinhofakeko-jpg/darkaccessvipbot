import os
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================== VARIÁVEIS DE AMBIENTE ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# ================== PLANOS ==================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90},
}

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📌 Ver planos", callback_data="plans")]
    ]
    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== MOSTRAR PLANOS ==================
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

# ================== CRIAR PIX (CORRIGIDO) ==================
def create_pix(plan_key, user_id):
    plan = PLANS[plan_key]

    url = "https://api.mercadopago.com/v1/payments"

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        # 🔥 ESSENCIAL PARA NÃO DAR ERRO 400
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

    response = requests.post(url, headers=headers, json=data)

    try:
        result = response.json()
    except Exception:
        return {"error": "Resposta inválida do Mercado Pago"}

    if response.status_code not in [200, 201]:
        print("❌ ERRO MERCADO PAGO:", result)

    return result

# ================== COMPRAR PLANO ==================
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
            "❌ *Erro ao gerar o PIX.*\nTente novamente em alguns segundos.",
            parse_mode="Markdown"
        )
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    keyboard = [
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]
    ]

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

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers).json()

    if response.get("status") == "approved":
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "✅ *Novo acesso aprovado*\n"
                f"Plano: {PLANS[plan_key]['name']}\n"
                f"Usuário: @{query.from_user.username or query.from_user.id}"
            ),
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            "✅ *Pagamento aprovado!*\n\nAcesso liberado.",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "⏳ Pagamento ainda não aprovado.\nTente novamente."
        )

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))

    app.run_polling()

if __name__ == "__main__":
    main()
