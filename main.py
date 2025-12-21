import os
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

MP_API = "https://api.mercadopago.com/v1/payments"

PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90},
}

USERS = {}

# 🔴 LINHA TEMPORÁRIA DE TESTE (REMOVER DEPOIS)
USERS[ADMIN_ID] = {"plan": "vip_vitalicio"}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 ACESSO VIP EXCLUSIVO\n\nClique abaixo:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text(
        "Escolha seu plano:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= CRIAR PIX =================
def criar_pix(plano_key, user_id):
    plano = PLANS[plano_key]
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }
    data = {
        "transaction_amount": float(plano["price"]),
        "description": plano["name"],
        "payment_method_id": "pix",
        "payer": {
            "email": f"user{user_id}@vip.com",
            "identification": {"type": "CPF", "number": "11111111111"}
        }
    }
    return requests.post(MP_API, headers=headers, json=data).json()

# ================= COMPRAR =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    # 🔐 BLINDAGEM DO VITALÍCIO
    if user_id in USERS and USERS[user_id]["plan"] == "vip_vitalicio":
        await q.edit_message_text(
            "👑 Você já possui VIP Vitalício.\n\n"
            "Não é necessário realizar nova compra."
        )
        return

    plan_key = q.data.replace("buy_", "")
    pix = criar_pix(plan_key, user_id)

    try:
        data = pix["point_of_interaction"]["transaction_data"]
        pix_code = data["qr_code"]
        payment_id = pix["id"]
    except:
        await q.edit_message_text("Erro ao gerar PIX.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    await q.edit_message_text(
        f"PIX:\n{pix_code}\n\nClique em verificar após pagar.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]]
        )
    )

# ================= VERIFICAR =================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    r = requests.get(
        f"{MP_API}/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    ).json()

    if r.get("status") == "approved":
        USERS[q.from_user.id] = {"plan": plan_key}
        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)
        await q.edit_message_text(f"Acesso liberado:\n{invite.invite_link}")
    else:
        await q.edit_message_text("Pagamento ainda não aprovado.")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))
    app.run_polling()

if __name__ == "__main__":
    main()
