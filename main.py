import os
import uuid
import asyncio
import requests
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberUpdated,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler,
)

# ================== VARIÁVEIS DE AMBIENTE ==================
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
        parse_mode="Markdown",
    )

# ================== PLANOS ==================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")],
    ]

    await query.edit_message_text(
        "📌 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

# ================== CRIAR PIX ==================
def create_pix(plan_key: str, user_id: int):
    plan = PLANS[plan_key]

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    data = {
        "transaction_amount": float(plan["price"]),
        "description": plan["name"],
        "payment_method_id": "pix",
        "external_reference": f"user_{user_id}_{plan_key}",
        "payer": {"email": f"user{user_id}@darkaccessvip.com"},
    }

    response = requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers=headers,
        json=data,
        timeout=15,
    )

    return response.json()

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
            parse_mode="Markdown",
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
        parse_mode="Markdown",
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
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
        timeout=15,
    ).json()

    if response.get("status") == "approved":
        plan = PLANS[plan_key]

        expires_at = (
            datetime.now() + timedelta(days=plan["days"])
            if plan["days"]
            else None
        )

        users = context.application.bot_data.setdefault("users", {})
        users[query.from_user.id] = {
            "expires": expires_at,
            "warned": False,
        }

        invite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
        )

        await query.edit_message_text(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Entre no grupo VIP:\n{invite.invite_link}",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "⏳ Pagamento ainda não aprovado.\nTente novamente."
        )

# ================== BOAS-VINDAS ==================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        update.chat_member.new_chat_member
        and update.chat_member.new_chat_member.status == "member"
    ):
        user = update.chat_member.new_chat_member.user
        await context.bot.send_message(
            chat_id=update.chat_member.chat.id,
            text=(
                f"👑 Bem-vindo ao *Dark Access VIP*, {user.first_name}!\n\n"
                "⚠️ Regras:\n"
                "• Conteúdo individual\n"
                "• Proibido repassar\n\n"
                "🔥 Aproveite!"
            ),
            parse_mode="Markdown",
        )

# ================== EXPIRAÇÃO + AVISO ==================
async def expiration_checker(app):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()
        users = app.bot_data.get("users", {})

        for user_id, data in list(users.items()):
            expires = data.get("expires")
            if not expires:
                continue

            # aviso 24h
            if not data.get("warned") and 0 < (expires - now).total_seconds() <= 86400:
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text="⏰ *Seu acesso VIP expira em menos de 24h!*",
                        parse_mode="Markdown",
                    )
                    data["warned"] = True
                except:
                    pass

            # expiração
            if now >= expires:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, user_id)
                    await asyncio.sleep(1)
                    await app.bot.unban_chat_member(GROUP_ID, user_id)
                    del users[user_id]
                except:
                    pass

# ================== START LOOP CORRETO ==================
async def post_init(app):
    app.create_task(expiration_checker(app))

# ================== MAIN ==================
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

    app.run_polling()

if __name__ == "__main__":
    main()
