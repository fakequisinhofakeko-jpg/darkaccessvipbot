import os
import uuid
import asyncio
import sqlite3
import requests
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================== CONFIG SAFE ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GROUP_ID_RAW = os.getenv("GROUP_ID")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não definido")

if not GROUP_ID_RAW or not ADMIN_ID_RAW:
    raise RuntimeError("GROUP_ID ou ADMIN_ID não definidos")

GROUP_ID = int(GROUP_ID_RAW)
ADMIN_ID = int(ADMIN_ID_RAW)

MP_API = "https://api.mercadopago.com/v1/payments"
DB_FILE = "database.db"

print("✅ Variáveis carregadas")

# ================== PLANOS ==================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90, "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90, "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90, "days": None},
}

# ================== DATABASE ==================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT,
    expires_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    plan TEXT,
    value REAL,
    date TEXT
)
""")

conn.commit()

# ================== HELPERS ==================
def get_user(user_id):
    cursor.execute("SELECT plan, expires_at FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def save_user(user_id, plan, expires):
    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan, expires)
    )
    conn.commit()

def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()

def log_payment(user_id, username, plan, value):
    cursor.execute(
        "INSERT INTO logs (user_id, username, plan, value, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, username or "-", plan, value, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n"
        "⚡ Liberação automática\n"
        "🔒 Conteúdo premium\n\n"
        "👇 Clique abaixo:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================== PLANOS ==================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text(
        "💥 *Escolha seu plano VIP:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================== MERCADO PAGO ==================
def criar_pix(plan_key, user_id):
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
        "payer": {
            "email": f"user{user_id}@vip.com",
            "identification": {"type": "CPF", "number": "11111111111"}
        }
    }

    return requests.post(MP_API, headers=headers, json=data, timeout=20).json()

# ================== COMPRAR ==================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    plan_key = q.data.replace("buy_", "")

    existing = get_user(user_id)
    if existing and existing[0] == "vip_vitalicio":
        await q.edit_message_text(
            "👑 *Você já possui VIP Vitalício.*",
            parse_mode="Markdown"
        )
        return

    pix = criar_pix(plan_key, user_id)

    try:
        data = pix["point_of_interaction"]["transaction_data"]
        pix_code = data["qr_code"]
        checkout = data.get("ticket_url")
        payment_id = pix["id"]
    except Exception:
        await q.edit_message_text("❌ Erro ao gerar pagamento.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    buttons = []
    if checkout:
        buttons.append([InlineKeyboardButton("💳 Pagar com cartão", url=checkout)])
    buttons.append([InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")])

    await q.edit_message_text(
        f"💳 *Pagamento VIP*\n\n"
        f"📌 Plano: {PLANS[plan_key]['name']}\n"
        f"💰 Valor: R${PLANS[plan_key]['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{pix_code}`",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ================== VERIFICAR ==================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    r = requests.get(
        f"{MP_API}/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
        timeout=15
    ).json()

    if r.get("status") == "approved":
        plan = PLANS[plan_key]
        expires = (
            (datetime.now() + timedelta(days=plan["days"])).isoformat()
            if plan["days"] else None
        )

        save_user(q.from_user.id, plan_key, expires)
        log_payment(q.from_user.id, q.from_user.username, plan["name"], plan["price"])

        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

        await q.edit_message_text(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Acesso liberado:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")

# ================== EXPIRAÇÃO ==================
async def expiration_loop(application):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()

        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for user_id, expires in cursor.fetchall():
            if datetime.fromisoformat(expires) <= now:
                try:
                    await application.bot.ban_chat_member(GROUP_ID, user_id)
                    await application.bot.unban_chat_member(GROUP_ID, user_id)
                except:
                    pass
                remove_user(user_id)

# ================== POST INIT ==================
async def post_init(application):
    application.create_task(expiration_loop(application))
    print("⏳ Expiração automática ativa")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))

    print("🤖 Bot iniciado")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
