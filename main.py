import os, json, uuid, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

CHECKOUT_LINKS = {
    "vip_1": os.getenv("CHECKOUT_VIP1"),
    "vip_3": os.getenv("CHECKOUT_VIP3"),
    "vip_vitalicio": os.getenv("CHECKOUT_VIPVIT"),
}

PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90},
}

DATA_FILE = "users.json"

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

USERS = load_users()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 ACESSO VIP EXCLUSIVO\n\n"
        "🔒 Conteúdo fechado\n"
        "⚡ Liberação automática\n\n"
        "👇 Clique abaixo:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = str(q.from_user.id)
    plano_atual = USERS.get(user_id)

    kb = []

    if plano_atual != "vip_vitalicio":
        if plano_atual is None:
            kb.append([InlineKeyboardButton("VIP 1 Mês – R$24,90", callback_data="buy_vip_1")])
            kb.append([InlineKeyboardButton("VIP 3 Meses – R$64,90", callback_data="buy_vip_3")])

        kb.append([InlineKeyboardButton("VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")])

    await q.edit_message_text(
        "💎 Escolha seu plano VIP:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= PAGAMENTO PIX =================
def criar_pix(plano, user_id):
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "transaction_amount": PLANS[plano]["price"],
        "description": PLANS[plano]["name"],
        "payment_method_id": "pix",
        "payer": {"email": f"user{user_id}@vip.com"}
    }
    r = requests.post("https://api.mercadopago.com/v1/payments", headers=headers, json=data)
    return r.json()

# ================= COMPRAR =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plano = q.data.replace("buy_", "")
    user_id = str(q.from_user.id)

    if USERS.get(user_id) == "vip_vitalicio":
        await q.edit_message_text("❌ Você já possui VIP Vitalício.")
        return

    pix = criar_pix(plano, user_id)

    try:
        pix_code = pix["point_of_interaction"]["transaction_data"]["qr_code"]
        payment_id = pix["id"]
    except:
        await q.edit_message_text("❌ Erro ao gerar PIX.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plano

    kb = [
        [InlineKeyboardButton("💳 Pagar com cartão", url=CHECKOUT_LINKS[plano])],
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]
    ]

    await q.edit_message_text(
        f"💳 Pagamento VIP\n\n"
        f"Plano: {PLANS[plano]['name']}\n"
        f"Valor: R${PLANS[plano]['price']}\n\n"
        f"PIX Copia e Cola:\n{pix_code}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= VERIFICAR =================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plano = context.user_data.get("plan")
    user_id = str(q.from_user.id)

    r = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    ).json()

    if r.get("status") == "approved":
        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)
        USERS[user_id] = plano
        save_users(USERS)

        await q.edit_message_text(
            f"✅ Pagamento aprovado!\n\n"
            f"Acesso VIP:\n{invite.invite_link}"
        )
    else:
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"👑 Painel Admin\n\n"
        f"/usuarios – listar\n"
        f"/remover ID – remover usuário"
    )

async def usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not USERS:
        await update.message.reply_text("Nenhum usuário ativo.")
        return

    msg = "Usuários VIP:\n\n"
    for u, p in USERS.items():
        msg += f"{u} — {p}\n"

    await update.message.reply_text(msg)

async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = context.args[0]
        await context.bot.ban_chat_member(GROUP_ID, int(uid))
        await context.bot.unban_chat_member(GROUP_ID, int(uid))
        USERS.pop(uid, None)
        save_users(USERS)
        await update.message.reply_text("Usuário removido.")
    except:
        await update.message.reply_text("Uso correto: /remover ID")

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
