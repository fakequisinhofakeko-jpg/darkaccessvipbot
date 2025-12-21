import os
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90},
}

USERS = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]

    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n"
        "🔒 Conteúdo fechado\n"
        "⚡ Acesso imediato após pagamento\n"
        "💎 Benefícios premium\n\n"
        "👇 Clique abaixo para ver os planos:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90 (Mais vendido)", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await query.edit_message_text(
        "💥 *Escolha seu plano VIP*\n\n"
        "⏳ Vagas limitadas\n"
        "🚀 Liberação automática\n\n"
        "👇 Selecione:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= PAGAMENTO =================
def create_payment(plan_key, user_id):
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
        "payer": {"email": f"user{user_id}@darkaccessvip.com"}
    }

    return requests.post(
        "https://api.mercadopago.com/v1/payments",
        headers=headers,
        json=data
    ).json()

# ================= COMPRAR =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("buy_", "")
    plan = PLANS[plan_key]

    payment = create_payment(plan_key, query.from_user.id)

    try:
        pix_code = payment["point_of_interaction"]["transaction_data"]["qr_code"]
        payment_id = payment["id"]
        checkout_link = payment["point_of_interaction"]["transaction_data"]["ticket_url"]
    except Exception:
        await query.edit_message_text("❌ Erro ao gerar pagamento.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    keyboard = [
        [InlineKeyboardButton("💳 Pagar com cartão", url=checkout_link)],
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]
    ]

    await query.edit_message_text(
        f"💳 *Pagamento VIP*\n\n"
        f"📌 Plano: {plan['name']}\n"
        f"💰 Valor: R${plan['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{pix_code}`\n\n"
        f"✅ Após pagar, clique em *Verificar pagamento*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= VERIFICAR =================
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
        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)
        USERS[query.from_user.id] = PLANS[plan_key]["name"]

        await query.edit_message_text(
            f"✅ *Pagamento aprovado!*\n\n"
            f"🔓 Acesso VIP liberado:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("⏳ Pagamento ainda não aprovado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"👑 *Painel Admin*\n\n"
        f"🆔 Admin ID: `{ADMIN_ID}`\n\n"
        f"/usuarios – listar usuários\n"
        f"/remover ID – remover usuário",
        parse_mode="Markdown"
    )

async def usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not USERS:
        await update.message.reply_text("Nenhum usuário ativo.")
        return

    texto = "👥 *Usuários VIP:*\n\n"
    for uid, plano in USERS.items():
        texto += f"🆔 {uid} — {plano}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        await context.bot.ban_chat_member(GROUP_ID, user_id)
        await context.bot.unban_chat_member(GROUP_ID, user_id)
        USERS.pop(user_id, None)
        await update.message.reply_text(f"✅ Usuário {user_id} removido.")
    except Exception:
        await update.message.reply_text("❌ Uso correto: /remover ID")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("usuarios", usuarios))
    app.add_handler(CommandHandler("remover", remover))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))

    app.run_polling()

if __name__ == "__main__":
    main()
