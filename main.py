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

# ================= PLANOS =================
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
        "⚡ Liberação automática\n"
        "💎 Benefícios premium\n\n"
        "👇 Clique abaixo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text(
        "💥 *Escolha seu plano VIP:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
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
            "email": f"user{user_id}@darkvip.com",
            "identification": {
                "type": "CPF",
                "number": "11111111111"
            }
        }
    }

    r = requests.post(MP_API, headers=headers, json=data, timeout=20)
    return r.json()

# ================= COMPRAR =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    plano = PLANS[plan_key]

    pix = criar_pix(plan_key, q.from_user.id)

    try:
        transaction = pix.get("point_of_interaction", {}).get("transaction_data", {})
        pix_code = transaction.get("qr_code") or transaction.get("qr_code_base64")
        checkout_link = transaction.get("ticket_url")
        payment_id = pix.get("id")

        if not pix_code or not payment_id:
            raise Exception("PIX inválido")

    except Exception:
        print("ERRO PIX:", pix)
        await q.edit_message_text("❌ Erro ao gerar PIX. Tente novamente.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    keyboard = [
        [InlineKeyboardButton("💳 Pagar com cartão", url=checkout_link)],
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]
    ]

    await q.edit_message_text(
        f"💳 *Pagamento VIP*\n\n"
        f"📌 Plano: {plano['name']}\n"
        f"💰 Valor: R${plano['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{pix_code}`\n\n"
        f"Após pagar, clique em *Verificar pagamento*.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= VERIFICAR =================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    if not payment_id:
        await q.edit_message_text("❌ Nenhum pagamento encontrado.")
        return

    r = requests.get(
        f"{MP_API}/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
        timeout=15
    ).json()

    if r.get("status") == "approved":
        invite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        USERS[q.from_user.id] = PLANS[plan_key]["name"]

        await q.edit_message_text(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Acesso liberado:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")

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
        texto += f"🆔 `{uid}` — {plano}\n"

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
